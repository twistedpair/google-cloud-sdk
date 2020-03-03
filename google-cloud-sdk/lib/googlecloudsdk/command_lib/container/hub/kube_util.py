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
"""Utils for Kubernetes Operations for GKE Hub commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import io
import os
import re

from googlecloudsdk.api_lib.container import api_adapter as gke_api_adapter
from googlecloudsdk.api_lib.container import kubeconfig as kconfig
from googlecloudsdk.api_lib.container import util as c_util
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.command_lib.container.hub import api_util as api_util
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core.util import encoding
from googlecloudsdk.core.util import files

NAMESPACE_DELETION_INITIAL_WAIT_MS = 0
NAMESPACE_DELETION_TIMEOUT_MS = 1000 * 60 * 2
NAMESPACE_DELETION_MAX_POLL_INTERVAL_MS = 1000 * 15
NAMESPACE_DELETION_INITIAL_POLL_INTERVAL_MS = 1000 * 5


class RBACError(exceptions.Error):
  """Class for errors raised by GKE Hub commands."""


class KubectlError(exceptions.Error):
  """Class for errors raised when shelling out to kubectl."""


def GetClusterUUID(kube_client):
  """Gets the UUID of the kube-system namespace.

  Args:
    kube_client: A KubernetesClient.

  Returns:
    the namespace UID

  Raises:
    exceptions.Error: If the UID cannot be acquired.
    calliope_exceptions.MinimumArgumentException: if a kubeconfig file cannot be
      deduced from the command line flags or environment
  """
  return kube_client.GetNamespaceUID('kube-system')


def DeleteNamespace(kube_client, namespace):
  """Delete a namespace from the cluster.

  Args:
    kube_client: The KubernetesClient towards the cluster.
    namespace: the namespace of connect agent deployment.

  Raises:
    exceptions.Error: if failed to delete the namespace.
  """
  if kube_client.NamespaceExists(namespace):
    try:
      succeeded, error = waiter.WaitFor(
          KubernetesPoller(),
          NamespaceDeleteOperation(namespace, kube_client),
          'Deleting namespace [{}] in the cluster'.format(namespace),
          pre_start_sleep_ms=NAMESPACE_DELETION_INITIAL_WAIT_MS,
          max_wait_ms=NAMESPACE_DELETION_TIMEOUT_MS,
          wait_ceiling_ms=NAMESPACE_DELETION_MAX_POLL_INTERVAL_MS,
          sleep_ms=NAMESPACE_DELETION_INITIAL_POLL_INTERVAL_MS)
    except waiter.TimeoutError:
      # waiter.TimeoutError assumes that the operation is a Google API
      # operation, and prints a debugging string to that effect.
      raise exceptions.Error(
          'Could not delete namespace [{}] from cluster.'.format(namespace))

    if not succeeded:
      raise exceptions.Error(
          'Could not delete namespace [{}] from cluster. Error: {}'.format(
              namespace, error))


class MembershipCRDCreationOperation(object):
  """An operation that waits for a membership CRD to be created."""

  CREATED_KEYWORD = 'unchanged'

  def __init__(self, kube_client, membership_crd_manifest):
    self.kube_client = kube_client
    self.done = False
    self.succeeded = False
    self.error = None
    self.membership_crd_manifest = membership_crd_manifest

  def __str__(self):
    return '<creating membership CRD>'

  def Update(self):
    """Updates this operation with the latest membership creation status."""
    out, err = self.kube_client.CreateMembershipCRD(
        self.membership_crd_manifest)
    if err:
      self.done = True
      self.error = err

    # If creation is successful, the create operation should show "unchanged"
    elif self.CREATED_KEYWORD in out:
      self.done = True
      self.succeeded = True


class KubeconfigProcessor(object):
  """A helper class that processes kubeconfig and context arguments."""

  def __init__(self):
    """Constructor for KubeconfigProcessor.

    Raises:
      exceptions.Error: if kubectl is not installed
    """
    # Warn if kubectl is not installed.
    if not c_util.CheckKubectlInstalled():
      raise exceptions.Error('kubectl not installed.')

  def GetKubeconfigAndContext(self, flags, temp_kubeconfig_dir):
    """Gets the kubeconfig and cluster context from arguments and defaults.

    Args:
      flags: the flags passed to the enclosing command. It must include
        kubeconfig and context.
      temp_kubeconfig_dir: a TemporaryDirectoryObject.

    Returns:
      the kubeconfig filepath and context name

    Raises:
      calliope_exceptions.MinimumArgumentException: if a kubeconfig file cannot
        be deduced from the command line flags or environment
      exceptions.Error: if the context does not exist in the deduced kubeconfig
        file
    """
    # Parsing flags to get the name and location of the GKE cluster to register
    if flags.gke_uri or flags.gke_cluster:
      location, name = _ParseGKEURI(
          flags.gke_uri) if flags.gke_uri else _ParseGKECluster(
              flags.gke_cluster)

      return _GetGKEKubeconfig(location, name, temp_kubeconfig_dir), None

    # We need to support in-cluster configuration so that gcloud can run from
    # a container on the Cluster we are registering. KUBERNETES_SERICE_PORT
    # and KUBERNETES_SERVICE_HOST environment variables are set in a kubernetes
    # cluster automatically, which can be used by kubectl to talk to
    # the API server.
    if not flags.kubeconfig and encoding.GetEncodedValue(
        os.environ, 'KUBERNETES_SERVICE_PORT') and encoding.GetEncodedValue(
            os.environ, 'KUBERNETES_SERVICE_HOST'):
      return None, None

    kubeconfig_file = (
        flags.kubeconfig or encoding.GetEncodedValue(os.environ, 'KUBECONFIG')
        or '~/.kube/config')

    kubeconfig = files.ExpandHomeDir(kubeconfig_file)
    if not kubeconfig:
      raise calliope_exceptions.MinimumArgumentException(
          ['--kubeconfig'],
          'Please specify --kubeconfig, set the $KUBECONFIG environment '
          'variable, or ensure that $HOME/.kube/config exists')
    kc = kconfig.Kubeconfig.LoadFromFile(kubeconfig)

    context_name = flags.context

    if context_name not in kc.contexts:
      raise exceptions.Error(
          'context [{}] does not exist in kubeconfig [{}]'.format(
              context_name, kubeconfig))

    return kubeconfig, context_name


# TODO(b/144528144): Remove the method when deprecating old beta commands
# as a last step.
class OldKubeconfigProcessor(object):
  """A helper class that processes kubeconfig and context arguments."""

  def __init__(self):
    """Constructor for KubeconfigProcessor.

    Raises:
      exceptions.Error: if kubectl is not installed
    """
    # Warn if kubectl is not installed.
    if not c_util.CheckKubectlInstalled():
      raise exceptions.Error('kubectl not installed.')

  def GetKubeconfigAndContext(self, flags):
    """Gets the kubeconfig and cluster context from arguments and defaults.

    Args:
      flags: the flags passed to the enclosing command. It must include
        kubeconfig and context.

    Returns:
      the kubeconfig filepath and context name

    Raises:
      calliope_exceptions.MinimumArgumentException: if a kubeconfig file cannot
        be deduced from the command line flags or environment
      exceptions.Error: if the context does not exist in the deduced kubeconfig
        file
    """
    # We need to support in-cluster configuration so that gcloud can run from
    # a container on the Cluster we are registering.
    if not flags.kubeconfig and encoding.GetEncodedValue(
        os.environ, 'KUBERNETES_SERVICE_PORT') and  encoding.GetEncodedValue(
            os.environ, 'KUBERNETES_SERVICE_HOST'):
      return None, None

    kubeconfig_file = (
        flags.kubeconfig or encoding.GetEncodedValue(os.environ, 'KUBECONFIG')
        or '~/.kube/config')

    kubeconfig = files.ExpandHomeDir(kubeconfig_file)
    if not kubeconfig:
      raise calliope_exceptions.MinimumArgumentException(
          ['--kubeconfig'],
          'Please specify --kubeconfig, set the $KUBECONFIG environment '
          'variable, or ensure that $HOME/.kube/config exists')
    kc = kconfig.Kubeconfig.LoadFromFile(kubeconfig)

    context_name = flags.context
    if not context_name:
      raise exceptions.Error('argument --context: Must be specified.')

    if context_name not in kc.contexts:
      raise exceptions.Error(
          'context [{}] does not exist in kubeconfig [{}]'.format(
              context_name, kubeconfig))

    return kubeconfig, context_name


class KubernetesPoller(waiter.OperationPoller):
  """An OperationPoller that polls operations targeting Kubernetes clusters."""

  def IsDone(self, operation):
    return operation.done

  def Poll(self, operation_ref):
    operation_ref.Update()
    return operation_ref

  def GetResult(self, operation):
    return (operation.succeeded, operation.error)


# TODO(b/144528144): Remove the method when deprecating old beta commands
# as a last step.
class OldKubernetesClient(object):
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

    processor = OldKubeconfigProcessor()
    self.kubeconfig, self.context = processor.GetKubeconfigAndContext(flags)

  def GetNamespaceUID(self, namespace):
    cmd = ['get', 'namespace', namespace, '-o', 'jsonpath=\'{.metadata.uid}\'']
    out, err = self._RunKubectl(cmd, None)
    if err:
      raise exceptions.Error(
          'Failed to get the UID of the cluster: {}'.format(err))
    return out.replace("'", '')

  def GetEvents(self, namespace):
    cmd = ['get',
           'events',
           '--namespace=' + namespace,
           "--sort-by='{.lastTimestamp}'"]
    out, err = self._RunKubectl(cmd, None)
    if err:
      raise exceptions.Error()
    return out

  def NamespacesWithLabelSelector(self, label):
    """Get the Connect Agent namespace by label.

    Args:
      label: the label used for namespace selection

    Raises:
      exceptions.Error: if failing to get namespaces.

    Returns:
      The first namespace with the label selector.
    """
    # Check if any namespace with label exists.
    out, err = self._RunKubectl(['get', 'namespaces', '--selector', label,
                                 '-o', 'jsonpath={.items}'], None)
    if err:
      raise exceptions.Error(
          'Failed to list namespaces in the cluster: {}'.format(err))
    if out == '[]':
      return []
    cmd = ['get', 'namespaces', '--selector', label, '-o',
           'jsonpath={.items[0].metadata.name}']
    out, err = self._RunKubectl(cmd, None)
    if err:
      raise exceptions.Error(
          'Failed to list namespaces in the cluster: {}'.format(err))
    return out.strip().split(' ') if out else []

  def DeleteMembership(self):
    _, err = self._RunKubectl(['delete', 'membership', 'membership'])
    return err

  def MembershipCRDExists(self):
    cmd = ['get', 'crds', 'memberships.hub.gke.io']
    _, err = self._RunKubectl(cmd, None)
    if err:
      if 'NotFound' in err:
        return False
      raise exceptions.Error('Error retrieving Membership CRD: {}'.format(err))
    return True

  def GetMembershipCR(self):
    """Get the YAML representation of the Membership CR."""
    cmd = ['get', 'membership', 'membership', '-o', 'yaml']
    out, err = self._RunKubectl(cmd, None)
    if err:
      if 'NotFound' in err:
        return ''
      raise exceptions.Error('Error retrieving membership CR: {}'.format(err))
    return out

  def GetMembershipCRD(self):
    """Get the YAML representation of the Membership CRD."""
    cmd = ['get', 'customresourcedefinition', 'memberships.hub.gke.io', '-o',
           'yaml']
    out, err = self._RunKubectl(cmd, None)
    if err:
      if 'NotFound' in err:
        return ''
      raise exceptions.Error('Error retrieving membership CRD: {}'.format(err))
    return out

  def GetMembershipOwnerID(self):
    """Looks up the owner id field in the Membership resource."""
    if not self.MembershipCRDExists():
      return None

    cmd = ['get', 'membership', 'membership', '-o', 'jsonpath={.spec.owner.id}']
    out, err = self._RunKubectl(cmd, None)
    if err:
      if 'NotFound' in err:
        return None
      raise exceptions.Error('Error retrieving membership id: {}'.format(err))
    return out

  def CreateMembershipCRD(self, membership_crd_manifest):
    return self.Apply(membership_crd_manifest)

  def ApplyMembership(self, membership_crd_manifest, membership_cr_manifest):
    """Apply membership resources."""
    if membership_crd_manifest:
      _, error = waiter.WaitFor(
          KubernetesPoller(),
          MembershipCRDCreationOperation(self, membership_crd_manifest),
          pre_start_sleep_ms=NAMESPACE_DELETION_INITIAL_WAIT_MS,
          max_wait_ms=NAMESPACE_DELETION_TIMEOUT_MS,
          wait_ceiling_ms=NAMESPACE_DELETION_MAX_POLL_INTERVAL_MS,
          sleep_ms=NAMESPACE_DELETION_INITIAL_POLL_INTERVAL_MS)
      if error:
        raise exceptions.Error(
            'Membership CRD creation failed to complete: {}'.format(error))
    if membership_cr_manifest:
      _, err = self.Apply(membership_cr_manifest)
      if err:
        raise exceptions.Error(
            'Failed to apply Membership CR to cluster: {}'.format(err))

  def NamespaceExists(self, namespace):
    _, err = self._RunKubectl(['get', 'namespace', namespace])
    return err is None

  def DeleteNamespace(self, namespace):
    _, err = self._RunKubectl(['delete', 'namespace', namespace])
    return err

  def GetResourceField(self, namespace, resource, json_path):
    """Returns the value of a field on a Kubernetes resource.

    Args:
      namespace: the namespace of the resource, or None if this resource is
        cluster-scoped
      resource: the resource, in the format <resourceType>/<name>; e.g.,
        'configmap/foo', or <resourceType> for a list of resources
      json_path: the JSONPath expression to filter with

    Returns:
      The field value (which could be empty if there is no such field), or
      the error printed by the command if there is an error.
    """
    cmd = ['-n', namespace] if namespace else []
    cmd.extend(['get', resource, '-o', 'jsonpath={{{}}}'.format(json_path)])
    return self._RunKubectl(cmd)

  def Apply(self, manifest):
    out, err = self._RunKubectl(['apply', '-f', '-'], stdin=manifest)
    return out, err

  def Delete(self, manifest):
    _, err = self._RunKubectl(['delete', '-f', '-'], stdin=manifest)
    return err

  def Logs(self, namespace, log_target):
    """Gets logs from a workload in the cluster.

    Args:
      namespace: the namespace from which to collect logs.
      log_target: the target for the logs command. Any target supported by
        'kubectl logs' is supported here.

    Returns:
      The logs, or an error if there was an error gathering these logs.
    """
    return self._RunKubectl(['logs', '-n', namespace, log_target])

  def _RunKubectl(self, args, stdin=None):
    """Runs a kubectl command with the cluster referenced by this client.

    Args:
      args: command line arguments to pass to kubectl
      stdin: text to be passed to kubectl via stdin

    Returns:
      The contents of stdout if the return code is 0, stderr (or a fabricated
      error if stderr is empty) otherwise
    """
    cmd = [c_util.CheckKubectlInstalled()]
    if self.kubeconfig and self.context:
      cmd.extend([
          '--context', self.context, '--kubeconfig', self.kubeconfig,
          '--request-timeout', self.kubectl_timeout
      ])

    cmd.extend(args)
    out = io.StringIO()
    err = io.StringIO()
    returncode = execution_utils.Exec(
        cmd, no_exit=True, out_func=out.write, err_func=err.write, in_str=stdin
    )

    if returncode != 0 and not err.getvalue():
      err.write('kubectl exited with return code {}'.format(returncode))

    return out.getvalue() if returncode == 0 else None, err.getvalue(
    ) if returncode != 0 else None


class KubernetesClient(object):
  """A client for accessing a subset of the Kubernetes API."""

  def __init__(self, flags):
    """Constructor for KubernetesClient.

    Args:
      flags: the flags passed to the enclosing command.

    Raises:
      exceptions.Error: if the client cannot be configured
      calliope_exceptions.MinimumArgumentException: if a kubeconfig file
        cannot be deduced from the command line flags or environment
    """
    self.kubectl_timeout = '20s'

    self.temp_kubeconfig_dir = None
    # If the cluster to be registered is a GKE cluster, create a temporary
    # directory to store the kubeconfig that will be generated using the
    # GKE GetCluster() API
    if flags and (flags.gke_uri or flags.gke_cluster):
      self.temp_kubeconfig_dir = files.TemporaryDirectory()

    processor = KubeconfigProcessor()
    self.kubeconfig, self.context = processor.GetKubeconfigAndContext(
        flags, self.temp_kubeconfig_dir)

  def __enter__(self):
    return self

  def __exit__(self, *_):
    # delete temp directory
    if self.temp_kubeconfig_dir is not None:
      self.temp_kubeconfig_dir.Close()

  def CheckClusterAdminPermissions(self):
    """Check to see if the user can perform all the actions in any namespace.

    Raises:
      KubectlError: if failing to get check for cluster-admin permissions.
      RBACError: if cluster-admin permissions are not found.
    """
    out, err = self._RunKubectl(['auth', 'can-i', '*', '*', '--all-namespaces'],
                                None)
    if err:
      raise KubectlError(
          'Failed to check if the user is a cluster-admin: {}'.format(err))

    if 'yes' not in out:
      raise RBACError(
          'Missing cluster-admin RBAC role: The cluster-admin role-based access'
          'control (RBAC) ClusterRole grants you the cluster permissions '
          'necessary to connect your clusters back to Google. \nTo create a '
          'ClusterRoleBinding resource in the cluster, run the following '
          'command:\n\n'
          'kubectl create clusterrolebinding [BINDING_NAME]  --clusterrole '
          'cluster-admin --user [USER]')

  def GetNamespaceUID(self, namespace):
    out, err = self._RunKubectl(
        ['get', 'namespace', namespace, '-o', 'jsonpath=\'{.metadata.uid}\''],
        None)
    if err:
      raise exceptions.Error(
          'Failed to get the UID of the cluster: {}'.format(err))
    return out.replace("'", '')

  def GetEvents(self, namespace):
    out, err = self._RunKubectl([
        'get', 'events', '--namespace=' + namespace,
        "--sort-by='{.lastTimestamp}'"
    ], None)
    if err:
      raise exceptions.Error()
    return out

  def NamespacesWithLabelSelector(self, label):
    """Get the Connect Agent namespace by label.

    Args:
      label: the label used for namespace selection

    Raises:
      exceptions.Error: if failing to get namespaces.

    Returns:
      The first namespace with the label selector.
    """
    # Check if any namespace with label exists.
    out, err = self._RunKubectl(['get', 'namespaces', '--selector', label,
                                 '-o', 'jsonpath={.items}'], None)
    if err:
      raise exceptions.Error(
          'Failed to list namespaces in the cluster: {}'.format(err))
    if out == '[]':
      return []
    out, err = self._RunKubectl([
        'get', 'namespaces', '--selector', label, '-o',
        'jsonpath={.items[0].metadata.name}'
    ], None)
    if err:
      raise exceptions.Error(
          'Failed to list namespaces in the cluster: {}'.format(err))
    return out.strip().split(' ') if out else []

  def DeleteMembership(self):
    _, err = self._RunKubectl(['delete', 'membership', 'membership'])
    return err

  def MembershipCRDExists(self):
    _, err = self._RunKubectl(
        ['get',
         'customresourcedefinitions.v1beta1.apiextensions.k8s.io',
         'memberships.hub.gke.io'], None)
    if err:
      if 'NotFound' in err:
        return False
      raise exceptions.Error('Error retrieving Membership CRD: {}'.format(err))
    return True

  def GetMembershipCR(self):
    """Get the YAML representation of the Membership CR."""
    out, err = self._RunKubectl(
        ['get', 'membership', 'membership', '-o', 'yaml'], None)
    if err:
      if 'NotFound' in err:
        return ''
      raise exceptions.Error('Error retrieving membership CR: {}'.format(err))
    return out

  def GetMembershipCRD(self):
    """Get the YAML representation of the Membership CRD."""
    out, err = self._RunKubectl([
        'get', 'customresourcedefinitions.v1beta1.apiextensions.k8s.io',
        'memberships.hub.gke.io', '-o', 'yaml'
    ], None)
    if err:
      if 'NotFound' in err:
        return ''
      raise exceptions.Error('Error retrieving membership CRD: {}'.format(err))
    return out

  def GetMembershipOwnerID(self):
    """Looks up the owner id field in the Membership resource."""
    if not self.MembershipCRDExists():
      return None

    out, err = self._RunKubectl(
        ['get', 'membership', 'membership', '-o', 'jsonpath={.spec.owner.id}'],
        None)
    if err:
      if 'NotFound' in err:
        return None
      raise exceptions.Error('Error retrieving membership id: {}'.format(err))
    return out

  def CreateMembershipCRD(self, membership_crd_manifest):
    return self.Apply(membership_crd_manifest)

  def ApplyMembership(self, membership_crd_manifest, membership_cr_manifest):
    """Apply membership resources."""
    if membership_crd_manifest:
      _, error = waiter.WaitFor(
          KubernetesPoller(),
          MembershipCRDCreationOperation(self, membership_crd_manifest),
          pre_start_sleep_ms=NAMESPACE_DELETION_INITIAL_WAIT_MS,
          max_wait_ms=NAMESPACE_DELETION_TIMEOUT_MS,
          wait_ceiling_ms=NAMESPACE_DELETION_MAX_POLL_INTERVAL_MS,
          sleep_ms=NAMESPACE_DELETION_INITIAL_POLL_INTERVAL_MS)
      if error:
        raise exceptions.Error(
            'Membership CRD creation failed to complete: {}'.format(error))
    if membership_cr_manifest:
      _, err = self.Apply(membership_cr_manifest)
      if err:
        raise exceptions.Error(
            'Failed to apply Membership CR to cluster: {}'.format(err))

  def NamespaceExists(self, namespace):
    _, err = self._RunKubectl(['get', 'namespace', namespace])
    return err is None

  def DeleteNamespace(self, namespace):
    _, err = self._RunKubectl(['delete', 'namespace', namespace])
    return err

  def GetResourceField(self, namespace, resource, json_path):
    """Returns the value of a field on a Kubernetes resource.

    Args:
      namespace: the namespace of the resource, or None if this resource is
        cluster-scoped
      resource: the resource, in the format <resourceType>/<name>; e.g.,
        'configmap/foo', or <resourceType> for a list of resources
      json_path: the JSONPath expression to filter with

    Returns:
      The field value (which could be empty if there is no such field), or
      the error printed by the command if there is an error.
    """
    cmd = ['-n', namespace] if namespace else []
    cmd.extend(['get', resource, '-o', 'jsonpath={{{}}}'.format(json_path)])
    return self._RunKubectl(cmd)

  def Apply(self, manifest):
    out, err = self._RunKubectl(['apply', '-f', '-'], stdin=manifest)
    return out, err

  def Delete(self, manifest):
    _, err = self._RunKubectl(['delete', '-f', '-'], stdin=manifest)
    return err

  def Logs(self, namespace, log_target):
    """Gets logs from a workload in the cluster.

    Args:
      namespace: the namespace from which to collect logs.
      log_target: the target for the logs command. Any target supported by
        'kubectl logs' is supported here.

    Returns:
      The logs, or an error if there was an error gathering these logs.
    """
    return self._RunKubectl(['logs', '-n', namespace, log_target])

  def _RunKubectl(self, args, stdin=None):
    """Runs a kubectl command with the cluster referenced by this client.

    Args:
      args: command line arguments to pass to kubectl
      stdin: text to be passed to kubectl via stdin

    Returns:
      The contents of stdout if the return code is 0, stderr (or a fabricated
      error if stderr is empty) otherwise
    """
    cmd = [c_util.CheckKubectlInstalled()]
    if self.context:
      cmd.extend(['--context', self.context])

    if self.kubeconfig:
      cmd.extend(['--kubeconfig', self.kubeconfig])

    cmd.extend(['--request-timeout', self.kubectl_timeout])
    cmd.extend(args)
    out = io.StringIO()
    err = io.StringIO()
    returncode = execution_utils.Exec(
        cmd, no_exit=True, out_func=out.write, err_func=err.write, in_str=stdin
    )

    if returncode != 0 and not err.getvalue():
      err.write('kubectl exited with return code {}'.format(returncode))

    return out.getvalue() if returncode == 0 else None, err.getvalue(
    ) if returncode != 0 else None


class DeploymentPodsAvailableOperation(object):
  """An operation that tracks whether a Deployment's Pods are all available."""

  def __init__(self, namespace, deployment_name, image, kube_client):
    self.namespace = namespace
    self.deployment_name = deployment_name
    self.image = image
    self.kube_client = kube_client
    self.done = False
    self.succeeded = False
    self.error = None

  def __str__(self):
    return '<Pod availability for {}/{}>'.format(self.namespace,
                                                 self.deployment_name)

  def Update(self):
    """Updates this operation with the latest Deployment availability status."""
    deployment_resource = 'deployment/{}'.format(self.deployment_name)

    def _HandleErr(err):
      """Updates the operation for the provided error."""
      # If the deployment hasn't been created yet, then wait for it to be.
      if 'NotFound' in err:
        return

      # Otherwise, fail the operation.
      self.done = True
      self.succeeded = False
      self.error = err

    # Ensure that the Deployment has the correct image, so that this operation
    # is tracking the status of a new rollout, not the pre-rollout steady state.
    # TODO(b/135121228): Check the generation vs observedGeneration as well.
    deployment_image, err = self.kube_client.GetResourceField(
        self.namespace, deployment_resource,
        '.spec.template.spec.containers[0].image')
    if err:
      _HandleErr(err)
      return
    if deployment_image != self.image:
      return

    spec_replicas, err = self.kube_client.GetResourceField(
        self.namespace, deployment_resource, '.spec.replicas')
    if err:
      _HandleErr(err)
      return

    status_replicas, err = self.kube_client.GetResourceField(
        self.namespace, deployment_resource, '.status.replicas')
    if err:
      _HandleErr(err)
      return

    available_replicas, err = self.kube_client.GetResourceField(
        self.namespace, deployment_resource, '.status.availableReplicas')
    if err:
      _HandleErr(err)
      return

    updated_replicas, err = self.kube_client.GetResourceField(
        self.namespace, deployment_resource, '.status.updatedReplicas')
    if err:
      _HandleErr(err)
      return

    # This mirrors the replica-count logic used by kubectl rollout status:
    # https://github.com/kubernetes/kubernetes/blob/master/pkg/kubectl/rollout_status.go
    # Not enough replicas are up-to-date.
    if updated_replicas < spec_replicas:
      return
    # Replicas of an older version have not been turned down.
    if status_replicas > updated_replicas:
      return
    # Not enough replicas are up and healthy.
    if available_replicas < updated_replicas:
      return

    self.succeeded = True
    self.done = True


class NamespaceDeleteOperation(object):
  """An operation that waits for a namespace to be deleted."""

  def __init__(self, namespace, kube_client):
    self.namespace = namespace
    self.kube_client = kube_client
    self.done = False
    self.succeeded = False
    self.error = None

  def __str__(self):
    return '<deleting namespace {}>'.format(self.namespace)

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


def _ParseGKEURI(gke_uri):
  """The GKE resource URI can be of following types: zonal, regional or generic.

  zonal - */projects/{project_id}/zones/{zone}/clusters/{cluster_name}
  regional - */projects/{project_id}/regions/{zone}/clusters/{cluster_name}
  generic - */projects/{project_id}/locations/{zone}/clusters/{cluster_name}

  The expected patterns are matched to extract the cluster location and name.
  Args:
   gke_uri: GKE resource URI

  Returns:
    cluster location and name
  """
  zonal_uri_pattern = r'.*\/projects\/(.*)\/zones\/(.*)\/clusters\/(.*)'
  regional_uri_pattern = r'.*\/projects\/(.*)\/regions\/(.*)\/clusters\/(.*)'
  location_uri_pattern = r'.*\/projects\/(.*)\/locations\/(.*)\/clusters\/(.*)'

  zone_matcher = re.search(zonal_uri_pattern, gke_uri)
  if zone_matcher is not None:
    return zone_matcher.group(2), zone_matcher.group(3)

  region_matcher = re.search(regional_uri_pattern, gke_uri)
  if region_matcher is not None:
    return region_matcher.group(2), region_matcher.group(3)

  location_matcher = re.search(location_uri_pattern, gke_uri)
  if location_matcher is not None:
    return location_matcher.group(2), location_matcher.group(3)

  raise exceptions.Error(
      'argument --gke-uri: {} is invalid. '
      '--gke-uri must be of format: `https://container.googleapis.com/projects/my-project/locations/us-central1-a/clusters/my-cluster`. '
      'You can use command: `gcloud container clusters list --uri` to view the '
      'current GKE clusters in your project.'
      .format(gke_uri))


def _ParseGKECluster(gke_cluster):
  rgx = r'(.*)\/(.*)'
  cluster_matcher = re.search(rgx, gke_cluster)
  if cluster_matcher is not None:
    return cluster_matcher.group(1), cluster_matcher.group(2)
  raise exceptions.Error(
      'argument --gke-cluster: {} is invalid. --gke-cluster must be of format: '
      '`{{REGION OR ZONE}}/{{CLUSTER_NAME`}}`'.format(gke_cluster))


def _GetGKEKubeconfig(location_id,
                      cluster_id,
                      temp_kubeconfig_dir):
  """The kubeconfig of GKE Cluster is fetched using the GKE APIs.

  The 'KUBECONFIG' value in `os.environ` will be temporarily updated with
  the temporary kubeconfig's path if the kubeconfig arg is not None.
  Consequently, subprocesses started with
  googlecloudsdk.core.execution_utils.Exec will see the temporary KUBECONFIG
  environment variable.

  Using GKE APIs the GKE cluster is validated, and the ClusterConfig object, is
  persisted in the temporarily updated 'KUBECONFIG'.

  Args:
    location_id: string, the id of the location to which the cluster belongs
    cluster_id: string, the id of the cluster
    temp_kubeconfig_dir: TemporaryDirectory object

  Raises:
    Error: If unable to get credentials for kubernetes cluster.

  Returns:
    the path to the kubeconfig file
  """
  kubeconfig = os.path.join(temp_kubeconfig_dir.path, 'kubeconfig')
  old_kubeconfig = encoding.GetEncodedValue(os.environ,
                                            'KUBECONFIG')
  try:
    encoding.SetEncodedValue(os.environ, 'KUBECONFIG', kubeconfig)
    gke_api = gke_api_adapter.NewAPIAdapter('v1')
    cluster_ref = gke_api.ParseCluster(cluster_id, location_id)
    cluster = gke_api.GetCluster(cluster_ref)
    auth = cluster.masterAuth
    valid_creds = auth and auth.clientCertificate and auth.clientKey
    # c_util.ClusterConfig.UseGCPAuthProvider() checks for
    # container/use_client_certificate setting
    if not valid_creds and not c_util.ClusterConfig.UseGCPAuthProvider():
      raise c_util.Error(
          'Unable to get cluster credentials. User must have edit '
          'permission on {}'.format(cluster_ref.projectId))
    c_util.ClusterConfig.Persist(cluster, cluster_ref.projectId)
  finally:
    if old_kubeconfig:
      encoding.SetEncodedValue(os.environ, 'KUBECONFIG', old_kubeconfig)
    else:
      del os.environ['KUBECONFIG']
  return kubeconfig


def GKEClusterSelfLink(args, project):
  """Returns the selfLink of a cluster, if it is a GKE cluster.

     It also incidentally validates the args.

  Args:
    args: an argparse namespace. All arguments that were provided to this
      command invocation.
    project: project ID.

  Returns:
    the full OnePlatform resource path of a GKE cluster, e.g.,
    //container.googleapis.com/project/p/location/l/cluster/c. If the cluster is
    not a GKE cluster, returns None.
  """
  if args.context:
    return None

  if args.gke_uri:
    location, cluster_name = _ParseGKEURI(args.gke_uri)
    return api_util.GetEffectiveResourceEndpoint(project, location,
                                                 cluster_name)

  if args.gke_cluster:
    location, cluster_name = _ParseGKECluster(args.gke_cluster)
    return api_util.GetEffectiveResourceEndpoint(project, location,
                                                 cluster_name)


def ValidateClusterIdentifierFlags(kube_client, args):
  """Validates if --gke-cluster | --gke-uri is supplied for GKE cluster, and --context for non GKE clusters.

  Args:
    kube_client: A Kubernetes client for the cluster to be registered.
    args: An argparse namespace. All arguments that were provided to this
      command invocation.

  Raises:
    calliope_exceptions.ConflictingArgumentsException: --context, --gke-uri,
    --gke-cluster are conflicting arguments.
    calliope_exceptions.ConflictingArgumentsException is raised if more than
    one of these arguments is set.

    calliope_exceptions.InvalidArgumentException is raised if --context is set
    for non GKE clusters.
  """
  is_gke_cluster = IsGKECluster(kube_client)
  if args.context and is_gke_cluster:
    raise calliope_exceptions.InvalidArgumentException(
        '--context', '--context cannot be used for GKE clusters. '
        'Either --gke-uri | --gke-cluster must be specified')

  if args.gke_uri and not is_gke_cluster:
    raise calliope_exceptions.InvalidArgumentException(
        '--gke-uri', 'use --context for non GKE clusters.')

  if args.gke_cluster and not is_gke_cluster:
    raise calliope_exceptions.InvalidArgumentException(
        '--gke-cluster', 'use --context for non GKE clusters.')


def IsGKECluster(kube_client):
  """Returns true if the cluster to be registered is a GKE cluster.

  There is no straightforward way to obtain this information from the cluster
  API server directly. This method uses metadata on the Kubernetes nodes to
  determine the instance ID. The instance ID field is unique to GKE clusters:
  Kubernetes-on-GCE clusters do not have this field.

  Args:
    kube_client: A Kubernetes client for the cluster to be registered.

  Raises:
      exceptions.Error: if failing there's a permission error or for invalid
      command.

  Returns:
    bool: True if kubeclient communicates with a GKE Cluster, false otherwise.
  """
  vm_instance_id, err = kube_client.GetResourceField(
      None, 'nodes',
      '.items[0].metadata.annotations.container\\.googleapis\\.com/instance_id')

  if err:
    raise exceptions.Error(
        'kubectl returned non-zero status code: {}'.format(err))

  if not vm_instance_id:
    return False
  return True
