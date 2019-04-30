# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Utils for GKE Hub commands."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import base64
import os
import subprocess
import tempfile
import textwrap
import uuid

from containerregistry.client import docker_name
from containerregistry.client.v2_2 import docker_image
from googlecloudsdk.api_lib.container import kubeconfig as kconfig
from googlecloudsdk.api_lib.container import util as c_util
from googlecloudsdk.api_lib.container.images import util as i_util
from googlecloudsdk.api_lib.util import apis as core_apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.command_lib.projects import util as p_util
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import http
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.util import files
from googlecloudsdk.core.util import times

AGENT_POD_LABEL = 'gke_connect_agent'

# The name of the secret that will store the Docker private registry
# credentials, if they are provided.
IMAGE_PULL_SECRET_NAME = 'connect-image-pull-secret'

CONNECT_RESOURCE_LABEL = 'hub.gke.io/project'

MANIFEST_SAVED_MESSAGE = """\
Manifest saved to [{0}]. Please apply the manifest to your cluster with \
`kubectl apply -f {0}`. You must have `cluster-admin` privilege in order to \
deploy the manifest.

**This file contains sensitive data; please treat it with the same discretion \
as your service account key file.**"""

# The components of the install manifest that will be removed by gcloud if the
# pod completes successfully. This does not include all of the components
# related to the pod, since some of these are removed by the pod itself.
INSTALL_POD_MANIFEST_TEMPLATE = """\
apiVersion: v1
kind: Pod
metadata:
  name: {agent_pod_name}
  namespace: {namespace}
  labels:
    app: {agent_app_label}
spec:
  restartPolicy: Never
  containers:
  - name: connect-agent
    image: {image}
    command:
    - gkeconnect_bin/bin/gkeconnect_agent
    - --install
    - --config
    - user-config
    imagePullPolicy: Always
    env:
    - name: MY_POD_NAMESPACE
      valueFrom:
        fieldRef:
          fieldPath: metadata.namespace"""

# The components of the install manifest that are created by gcloud and are
# either not deleted or deleted by the pod itself.
MANIFEST_TEMPLATE_FOR_NON_DELETED_RESOURCES = """
apiVersion: v1
kind: ConfigMap
metadata:
  name: user-config
  namespace: {namespace}
data:
  project_id: "{project_id}"
  project_number: "{project_number}"
  membership_name: "{membership_name}"
  proxy: "{proxy}"
  image: "{image}"
binaryData:
  gcp_sa_key: "{gcp_sa_key}"
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: {project_id}-gke-connect-agent-role-binding
  labels:
    {connect_resource_label}: {project_id}
subjects:
- kind: ServiceAccount
  name: default
  namespace: {namespace}
roleRef:
  kind: ClusterRole
  name: cluster-admin
  apiGroup: rbac.authorization.k8s.io"""

# The secret that will be installed if a Docker registry credential is provided.
IMAGE_PULL_SECRET_TEMPLATE = """\
apiVersion: v1
kind: Secret
metadata:
  name: {name}
  namespace: {namespace}
  labels:
    {connect_resource_label}: {project_id}
data:
  .dockerconfigjson: {image_pull_secret}
type: kubernetes.io/dockerconfigjson"""

# The namespace that will be created, and in which the Connect agent pod will
# be run.
NAMESPACE_MANIFEST_TEMPLATE = """\
apiVersion: v1
kind: Namespace
metadata:
  name: {namespace}
  labels:
    {connect_resource_label}: {project_id}"""

AGENT_POD_INITIAL_WAIT_MS = 1000 * 2
AGENT_POD_TIMEOUT_MS = 1000 * 45
AGENT_POD_MAX_POLL_INTERVAL_MS = 1000 * 3
AGENT_POD_INITIAL_POLL_INTERVAL_MS = 1000 * 1

NAMESPACE_DELETION_INITIAL_WAIT_MS = 0
NAMESPACE_DELETION_TIMEOUT_MS = 1000 * 60 * 2
NAMESPACE_DELETION_MAX_POLL_INTERVAL_MS = 1000 * 15
NAMESPACE_DELETION_INITIAL_POLL_INTERVAL_MS = 1000 * 5

# The Connect agent image to use by default.
DEFAULT_CONNECT_AGENT_IMAGE = 'gcr.io/gkeconnect/gkeconnect-gce'
# The Connect agent image tag to use by default.
DEFAULT_CONNECT_AGENT_TAG = 'release'


def AddCommonArgs(parser):
  """Adds the flags shared between 'hub' subcommands to parser.

  Args:
    parser: an argparse.ArgumentParser, to which the common flags will be added
  """
  parser.add_argument(
      '--context',
      required=True,
      type=str,
      help=textwrap.dedent("""\
          The context in the kubeconfig file that specifies the cluster.
        """),
  )
  parser.add_argument(
      '--kubeconfig-file',
      type=str,
      help=textwrap.dedent("""\
          The kubeconfig file containing an entry for the cluster. Defaults to
          $KUBECONFIG if it is set in the environment, otherwise defaults to
          to $HOME/.kube/config.
        """),
  )


def _MembershipClient():
  return core_apis.GetClientInstance('gkehub', 'v1beta1')


def CreateMembership(project, membership_id, description):
  """Creates a Membership resource in the GKE Hub API.

  Args:
    project: the project in which to create the membership
    membership_id: the value to use for the membership_id
    description: the value to put in the description field

  Returns:
    the created Membership resource.

  Raises:
    - apitools.base.py.HttpError: if the request returns an HTTP error
    - exceptions raised by waiter.WaitFor()
  """
  client = _MembershipClient()
  request = client.MESSAGES_MODULE.GkehubProjectsLocationsGlobalMembershipsCreateRequest(
      membership=client.MESSAGES_MODULE.Membership(description=description),
      parent='projects/{}/locations/global'.format(project),
      membershipId=membership_id,
  )
  op = client.projects_locations_global_memberships.Create(request)
  op_resource = resources.REGISTRY.ParseRelativeName(
      op.name, collection='gkehub.projects.locations.operations')
  return waiter.WaitFor(
      waiter.CloudOperationPoller(client.projects_locations_global_memberships,
                                  client.projects_locations_operations),
      op_resource, 'Waiting for membership to be created')


def GetMembership(name):
  """Gets a Membership resource from the GKE Hub API.

  Args:
    name: the full resource name of the membership to get, e.g.,
      projects/foo/locations/global/memberships/name.

  Returns:
    a Membership resource

  Raises:
    apitools.base.py.HttpError: if the request returns an HTTP error
  """

  client = _MembershipClient()
  return client.projects_locations_global_memberships.Get(
      client.MESSAGES_MODULE.GkehubProjectsLocationsGlobalMembershipsGetRequest(
          name=name))


def DeleteMembership(name):
  """Deletes a membership from the GKE Hub.

  Args:
    name: the full resource name of the membership to delete, e.g.,
      projects/foo/locations/global/memberships/name.

  Raises:
    apitools.base.py.HttpError: if the request returns an HTTP error
  """

  client = _MembershipClient()
  op = client.projects_locations_global_memberships.Delete(
      client.MESSAGES_MODULE
      .GkehubProjectsLocationsGlobalMembershipsDeleteRequest(name=name))
  op_resource = resources.REGISTRY.ParseRelativeName(
      op.name, collection='gkehub.projects.locations.operations')
  waiter.WaitFor(
      waiter.CloudOperationPollerNoResources(
          client.projects_locations_operations), op_resource,
      'Waiting for membership to be deleted')


def GetClusterUUID(args):
  """Gets the UUID of the kube-system namespace.

  Args:
    args: command line arguments

  Returns:
    the namespace UID

  Raises:
    exceptions.Error: If the UID cannot be acquired.
    calliope_exceptions.MinimumArgumentException: if a kubeconfig file cannot be
      deduced from the command line flags or environment
  """
  return KubernetesClient(args).GetNamespaceUID('kube-system')


def ImageDigestForContainerImage(name, tag):
  """Given a container image and tag, returns the digest for that image version.

  Args:
    name: the gcr.io registry name plus the image name
    tag: the image tag

  Returns:
    The digest of the image, or None if there is no such image.

  Raises:
    googlecloudsdk.core.UnsupportedRegistryError: If the path is valid,
      but belongs to an unsupported registry.
    i_util.InvalidImageNameError: If the image name is invalid.
    i_util.TokenRefreshError: If there is an error refreshing credentials
      needed to access the GCR repo.
    i_util.UserRecoverableV2Error: If a user-recoverable error occurs accessing
      the GCR repo.
  """

  def _TaggedImage():
    """Display the fully-qualified name."""
    return '{}:{}'.format(name, tag)

  name = i_util.ValidateRepositoryPath(name)
  with i_util.WrapExpectedDockerlessErrors(name):
    with docker_image.FromRegistry(
        basic_creds=i_util.CredentialProvider(),
        name=docker_name.Tag(_TaggedImage()),
        transport=http.Http()) as r:
      return r.digest()


def GenerateInstallManifest(project_id, namespace, image, sa_key_data,
                            image_pull_secret_data, membership_name, proxy):
  """Generates the contents of the GKE Connect agent install manifest.

  Args:
    project_id: The GCP project identifier.
    namespace: The namespace into which to deploy the Connect agent.
    image: The container image to use in the Connect agent pod (and, later,
      deployment).
    sa_key_data: The contents of a GCP SA keyfile, base64-encoded.
    image_pull_secret_data: The contents of a secret that will be used as an
      image pull secret for the provided Docker image.
    membership_name: The name of the membership that this manifest is being
      generated for.
    proxy: The HTTP proxy that the agent should use, in the form
      http[s]://<proxy>

  Returns:
    A tuple, containing (
      a string, a YAML manifest that can be used to install the agent,
      a string, the subset of the manifest that relates to the agent install
        pod, and can be reverted,
      the name of the connect agent install pod
    )
  """
  project_number = p_util.GetProjectNumber(project_id)
  agent_pod_name = 'gke-connect-agent-{}'.format(uuid.uuid4().hex)

  namespace_manifest = NAMESPACE_MANIFEST_TEMPLATE.format(
      connect_resource_label=CONNECT_RESOURCE_LABEL,
      namespace=namespace,
      project_id=project_id)

  pod_manifest = INSTALL_POD_MANIFEST_TEMPLATE.format(
      namespace=namespace,
      agent_pod_name=agent_pod_name,
      agent_app_label=AGENT_POD_LABEL,
      project_id=project_id,
      image=image)

  non_deleted_resources_manifest = MANIFEST_TEMPLATE_FOR_NON_DELETED_RESOURCES.format(
      connect_resource_label=CONNECT_RESOURCE_LABEL,
      namespace=namespace,
      project_id=project_id,
      project_number=project_number,
      membership_name=membership_name or '',
      proxy=proxy or '',
      image=image,
      gcp_sa_key=sa_key_data)

  if image_pull_secret_data:
    # The indentation of this string literal is important: it must be
    # appendable to the bottom of the pod_manifest.
    image_pull_secret_section = """\
  imagePullSecrets:
    - name: {}""".format(IMAGE_PULL_SECRET_NAME)

    pod_manifest = '{}\n{}\n---\n{}'.format(
        pod_manifest, image_pull_secret_section,
        IMAGE_PULL_SECRET_TEMPLATE.format(
            name=IMAGE_PULL_SECRET_NAME,
            connect_resource_label=CONNECT_RESOURCE_LABEL,
            namespace=namespace,
            project_id=project_id,
            image_pull_secret=image_pull_secret_data))

  return '{}\n---\n{}\n---\n{}'.format(
      namespace_manifest, pod_manifest,
      non_deleted_resources_manifest), pod_manifest, agent_pod_name


def Base64EncodedFileContents(filename):
  """Reads the provided file, and returns its contents, base64-encoded.

  Args:
    filename: The path to the file, absolute or relative to the current working
      directory.

  Returns:
    A string, the contents of filename, base64-encoded.

  Raises:
   files.Error: if the file cannot be read.
  """
  return base64.b64encode(
      files.ReadBinaryFileContents(files.ExpandHomeDir(filename)))


def DeployConnectAgent(args,
                       service_account_key_data,
                       docker_credential_data,
                       upgrade=False):
  """Deploys the GKE Connect agent to the cluster.

  Args:
    args: arguments of the command.
    service_account_key_data: The contents of a Google IAM service account JSON
      file
    docker_credential_data: A credential that can be used to access Docker, to
      be stored in a secret and referenced from pod.spec.ImagePullSecrets.
    upgrade: whether to attempt to upgrade the agent, rather than replacing it.

  Raises:
    exceptions.Error: If the agent cannot be deployed properly
    calliope_exceptions.MinimumArgumentException: If the agent cannot be
    deployed properly
  """
  kube_client = KubernetesClient(args)

  image = args.docker_image
  if not image:
    # Get the SHA for the default image.
    try:
      digest = ImageDigestForContainerImage(DEFAULT_CONNECT_AGENT_IMAGE,
                                            DEFAULT_CONNECT_AGENT_TAG)
      image = '{}@{}'.format(DEFAULT_CONNECT_AGENT_IMAGE, digest)
    except Exception as exp:
      raise exceptions.Error(
          'could not determine image digest for {}:{}: {}'.format(
              DEFAULT_CONNECT_AGENT_IMAGE, DEFAULT_CONNECT_AGENT_TAG, exp))

  project_id = properties.VALUES.core.project.GetOrFail()
  namespace = _GKEConnectNamespace(kube_client, project_id)

  full_manifest, pod_manifest, agent_pod_name = GenerateInstallManifest(
      project_id, namespace, image, service_account_key_data,
      docker_credential_data, args.CLUSTER_NAME, args.proxy)

  # Generate a manifest file if necessary.
  if args.manifest_output_file:
    try:
      files.WriteFileContents(
          files.ExpandHomeDir(args.manifest_output_file),
          full_manifest,
          private=True)
    except files.Error as e:
      exceptions.Error('could not create manifest file: {}'.format(e))

    log.status.Print(MANIFEST_SAVED_MESSAGE.format(args.manifest_output_file))
    return

  log.status.Print('Deploying GKE Connect agent pod to cluster...')

  # During an upgrade, the namespace should not be deleted.
  if not upgrade:
    # Delete the ns if necessary
    if kube_client.NamespaceExists(namespace):
      console_io.PromptContinue(
          message='Namespace [{namespace}] already exists in the cluster. This '
          'may be from a previous installation of the agent. If you want to '
          'investigate, enter "n" and run\n\n'
          '  kubectl \\\n'
          '    --kubeconfig={kubeconfig} \\\n'
          '    --context={context} \\\n'
          '    get all -n {namespace}\n\n'
          'Continuing will delete namespace [{namespace}].'.format(
              namespace=namespace,
              kubeconfig=kube_client.kubeconfig,
              context=kube_client.context),
          cancel_on_no=True)
      try:
        succeeded, error = waiter.WaitFor(
            KubernetesPodPoller(),
            NamespaceDeleteOperation(namespace, kube_client),
            'Deleting namespace [{}] in the cluster'.format(namespace),
            pre_start_sleep_ms=NAMESPACE_DELETION_INITIAL_WAIT_MS,
            max_wait_ms=NAMESPACE_DELETION_TIMEOUT_MS,
            wait_ceiling_ms=NAMESPACE_DELETION_MAX_POLL_INTERVAL_MS,
            sleep_ms=NAMESPACE_DELETION_INITIAL_POLL_INTERVAL_MS)
      except waiter.TimeoutError as e:
        # waiter.TimeoutError assumes that the operation is a Google API
        # operation, and prints a debugging string to that effect.
        raise exceptions.Error(
            'Could not delete namespace [{}] from cluster.'.format(namespace))

      if not succeeded:
        raise exceptions.Error(
            'Could not delete namespace [{}] from cluster. Error: {}'.format(
                namespace, error))

  # Create the agent install pod and related resources.
  err = kube_client.Apply(full_manifest)
  if err:
    raise exceptions.Error(
        'Failed to apply manifest to cluster: {}'.format(err))

  kubectl_log_cmd = (
      'kubectl --kubeconfig={} --context={} logs -n {} -l app={}'.format(
          kube_client.kubeconfig, kube_client.context, namespace,
          AGENT_POD_LABEL))

  def _WriteAgentLogs():
    """Writes logs from the GKE Connect agent pod to a temporary file."""
    logs, err = kube_client.Logs(namespace, agent_pod_name)
    if err:
      log.warning('Could not fetch agent pod logs: {}'.format(err))
      return

    _, tmp_file = tempfile.mkstemp(
        suffix='_{}.log'.format(times.Now().strftime('%Y%m%d-%H%M%S')),
        prefix='gke_connect_',
    )
    files.WriteFileContents(tmp_file, logs, private=True)
    log.status.Print('GKE Connect pod logs saved to [{}]'.format(tmp_file))

  try:
    succeeded, error = waiter.WaitFor(
        KubernetesPodPoller(),
        ConnectAgentPodOperation(namespace, agent_pod_name, kube_client),
        'Waiting for GKE Connect agent pod to complete',
        pre_start_sleep_ms=AGENT_POD_INITIAL_WAIT_MS,
        max_wait_ms=AGENT_POD_TIMEOUT_MS,
        wait_ceiling_ms=AGENT_POD_MAX_POLL_INTERVAL_MS,
        sleep_ms=AGENT_POD_INITIAL_POLL_INTERVAL_MS)
  except waiter.TimeoutError:
    # waiter.TimeoutError assumes that the operation is a Google API operation,
    # and prints a debugging string to that effect.
    _WriteAgentLogs()
    raise exceptions.Error(
        'GKE Connect pod timed out. Leaving pod in cluster for further '
        'debugging.\nTo view logs from the cluster:\n\n  {}\n'.format(
            kubectl_log_cmd))

  _WriteAgentLogs()

  if not succeeded:
    raise exceptions.Error(
        'GKE Connect pod did not succeed. Leaving pod in cluster for further '
        'debugging.\nTo view logs from the cluster: {}\nKubectl error log: {}'
        .format(kubectl_log_cmd, error))

  log.status.Print(
      'GKE Connect pod succeeded. Removing leftover resources from cluster.')
  err = kube_client.Delete(pod_manifest)
  if err:
    raise exceptions.Error('Failed to delete pod from cluster: {}'.format(err))


class NamespaceDeleteOperation(object):
  """An operation that waits for a namespace to be deleted."""

  def __init__(self, namespace, kube_client):
    self.namespace = namespace
    self.kube_client = kube_client
    self.done = False
    self.succeeded = False
    self.error = None

  def __str__(self):
    return '<deleting namespce {}>'.format(self.namespace)

  def Update(self):
    """Updates this operation with the latest namespace deletion status."""
    err = self.kube_client.DeleteNamespace(self.namespace)

    # The first delete request should succeed.
    if not err:
      return

    # If deletion is successful, the delete command will return a NotFound
    # error.
    if 'NotFound' in err:
      self.done = True
      self.succeeded = True
    else:
      self.error = err


class ConnectAgentPodOperation(object):
  """An operation that tracks the GKE Connect agent pod in the cluster."""

  def __init__(self, namespace, agent_pod_name, kube_client):
    self.namespace = namespace
    self.agent_pod_name = agent_pod_name
    self.kube_client = kube_client
    self.done = False
    self.succeeded = False
    self.error = None

  def __str__(self):
    return '<GKE Connect agent installer in namespace {}>'.format(
        self.namespace)

  def Update(self):
    """Updates this operation with the latest state of the agent pod."""
    out, err = self.kube_client.GetPodField(self.namespace, self.agent_pod_name,
                                            '.status.phase')
    if err:
      self.done = True
      self.succeeded = False
      self.error = err
      return

    # The .status.phase field contains one of five values. They map to the
    # staus of this operation as follows:
    #   - "Pending": operation is ongoing
    #   - "Running": operation is ongoing
    #   - "Succeeded": operation is complete, successfully
    #   - "Failed": operation is complete, unsuccessfully
    #   - "Unknown": operation is complete, unsuccessfully
    # The JSONPath expression above prints the value of the .status.phase field
    # (i.e., one of these five strings) to stdout
    if out == 'Pending' or out == 'Running':
      return

    self.done = True
    if out == 'Failed':
      self.succeeded = False
      # TODO(b/130295119): Is there a way to get a failure message?
      self.error = exceptions.Error('Connect agent pod failed.')
      return
    if out == 'Unknown':
      self.succeeded = False
      self.error = exceptions.Error('Connect agent pod in an unknown state.')
      return

    self.succeeded = True


class KubernetesPodPoller(waiter.OperationPoller):
  """An OperationPoller that polls ConnectAgentPodOperations."""

  def IsDone(self, operation):
    return operation.done

  def Poll(self, operation_ref):
    operation_ref.Update()
    return operation_ref

  def GetResult(self, operation):
    return (operation.succeeded, operation.error)


class KubernetesClient(object):
  """A client for accessing a subset of the Kubernetes API."""

  def __init__(self, flags):
    """Constructor for KubernetesClient.

    Args:
      flags: the flags passed to the enclosing command

    Raises:
      exceptions.Error: if the client cannot be configured
      calliope_exceptions.MinimumArgumentException: if a kubeconfig file
        cannot be deduced from the command line flags or environment
    """
    self.kubectl_timeout = '20s'

    # Warn if kubectl is not installed.
    if not c_util.CheckKubectlInstalled():
      raise exceptions.Error('kubectl not installed.')

    self.kubeconfig, self.context = self._GetKubeconfigAndContext(
        flags.kubeconfig_file, flags.context)

  def GetNamespaceUID(self, namespace):
    cmd = ['get', 'namespace', namespace, '-o', 'jsonpath=\'{.metadata.uid}\'']
    out, err = self._RunKubectl(cmd, None)
    if err:
      raise exceptions.Error(
          'Failed to get the UID of the cluster: {}'.format(err))

    return out.replace("'", '')

  def NamespacesWithLabelSelector(self, label):
    cmd = ['get', 'namespace', '-l', label, '-o', 'jsonpath={..metadata.name}']
    out, err = self._RunKubectl(cmd, None)
    if err:
      raise exceptions.Error(
          'Failed to list namespaces in the cluster: {}'.format(err))
    return out.strip().split(' ') if out else []

  def NamespaceExists(self, namespace):
    _, err = self._RunKubectl(['get', 'namespace', namespace])
    return err is None

  def DeleteNamespace(self, namespace):
    _, err = self._RunKubectl(['delete', 'namespace', namespace])
    return err

  def GetPodField(self, namespace, pod, json_path):
    cmd = [
        'get', 'pods', '-n', namespace, pod, '-o',
        'jsonpath={{{}}}'.format(json_path)
    ]
    return self._RunKubectl(cmd)

  def Apply(self, manifest):
    _, err = self._RunKubectl(['apply', '-f', '-'], stdin=manifest)
    return err

  def Delete(self, manifest):
    _, err = self._RunKubectl(['delete', '-f', '-'], stdin=manifest)
    return err

  def Logs(self, namespace, pod):
    return self._RunKubectl(['logs', '-n', namespace, pod])

  def _GetKubeconfigAndContext(self, kubeconfig_file, context):
    """Gets the kubeconfig and cluster context from arguments and defaults.

    Args:
      kubeconfig_file: The kubecontext file to use
      context: The value of the context flag

    Returns:
      the kubeconfig filepath and context name

    Raises:
      calliope_exceptions.MinimumArgumentException: if a kubeconfig file cannot
        be deduced from the command line flags or environment
      exceptions.Error: if the context does not exist in the deduced kubeconfig
        file
    """
    kubeconfig_file = (
        kubeconfig_file or os.getenv('KUBECONFIG') or '~/.kube/config')
    kubeconfig = files.ExpandHomeDir(kubeconfig_file)
    if not kubeconfig:
      raise calliope_exceptions.MinimumArgumentException(
          ['--kubeconfig-file'],
          'Please specify --kubeconfig, set the $KUBECONFIG environment '
          'variable, or ensure that $HOME/.kube/config exists')
    kc = kconfig.Kubeconfig.LoadFromFile(kubeconfig)

    context_name = context

    if context_name not in kc.contexts:
      raise exceptions.Error(
          'context [{}] does not exist in kubeconfig [{}]'.format(
              context_name, kubeconfig))

    return kubeconfig, context_name

  def _RunKubectl(self, args, stdin=None):
    """Runs a kubectl command with the cluster referenced by this client.

    Args:
      args: command line arguments to pass to kubectl
      stdin: text to be passed to kubectl via stdin

    Returns:
      The contents of stdout if the return code is 0, stderr (or a fabricated
      error if stderr is empty) otherwise
    """
    cmd = [
        c_util.CheckKubectlInstalled(), '--context', self.context,
        '--kubeconfig', self.kubeconfig, '--request-timeout',
        self.kubectl_timeout
    ]
    cmd.extend(args)

    p = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    out, err = p.communicate(stdin)

    if p.returncode != 0 and not err:
      err = 'kubectl exited with return code {}'.format(p.returncode)

    return out if p.returncode == 0 else None, err if p.returncode != 0 else None


def DeleteConnectNamespace(args):
  """Delete the namespace in the cluster that contains the connect agent.

  Args:
    args: an argparse namespace. All arguments that were provided to this
      command invocation.

  Raises:
    calliope_exceptions.MinimumArgumentException: if a kubeconfig file cannot
      be deduced from the command line flags or environment
  """

  kube_client = KubernetesClient(args)
  namespace = _GKEConnectNamespace(kube_client,
                                   properties.VALUES.core.project.GetOrFail())
  cleanup_msg = 'Please delete namespace {} manually in your cluster.'.format(
      namespace)

  err = kube_client.DeleteNamespace(namespace)
  if err:
    if 'NotFound' in err:
      # If the namespace was not found, then do not log an error.
      log.status.Print(
          'Namespace [{}] (for context [{}]) did not exist, so it did not '
          'require deletion.'.format(namespace, args.context))
      return
    log.warning(
        'Failed to delete namespace [{}] (for context [{}]): {}. {}'.format(
            namespace, args.context, err, cleanup_msg))
    return


def _GKEConnectNamespace(kube_client, project_id):
  """Returns the namespace into which to install or update the connect agent.

  Connect namespaces are identified by the presence of the hub.gke.io/project
  label. If there is one existing namespace with this label in the cluster, its
  name is returned; otherwise, a connect agent namespace with the project
  number as a suffix is returned. If there are multiple namespaces with the
  hub.gke.io/project label, an error is raised.

  Args:
    kube_client: a KubernetesClient
    project_id: A GCP project identifier

  Returns:
    a string, the namespace

  Raises:
    exceptions.Error: if there are multiple Connect namespaces in the cluster
  """
  selector = '{}={}'.format(CONNECT_RESOURCE_LABEL, project_id)
  namespaces = kube_client.NamespacesWithLabelSelector(selector)
  if not namespaces:
    return 'gke-connect-{}'.format(p_util.GetProjectNumber(project_id))
  if len(namespaces) == 1:
    return namespaces[0]
  raise exceptions.Error(
      'Multiple GKE Connect namespaces in cluster: {}'.format(namespaces))
