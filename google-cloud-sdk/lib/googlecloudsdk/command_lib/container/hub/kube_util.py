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

from googlecloudsdk.api_lib.container import kubeconfig as kconfig
from googlecloudsdk.api_lib.container import util as c_util
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core.util import files

NAMESPACE_DELETION_INITIAL_WAIT_MS = 0
NAMESPACE_DELETION_TIMEOUT_MS = 1000 * 60 * 2
NAMESPACE_DELETION_MAX_POLL_INTERVAL_MS = 1000 * 15
NAMESPACE_DELETION_INITIAL_POLL_INTERVAL_MS = 1000 * 5


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


def DeleteNamespaceForReinstall(kube_client, namespace):
  """Delete the existing connect namespace for reinstallation.

  Args:
    kube_client: The KubernetesClient towards the cluster.
    namespace: the namespace of connect agent deployment.

  Raises:
    exceptions.Error: if failed to delete the namespace
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
    if self.CREATED_KEYWORD in out:
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
    if not flags.kubeconfig and os.getenv(
        'KUBERNETES_SERVICE_PORT') and os.getenv('KUBERNETES_SERVICE_HOST'):
      return None, None

    kubeconfig_file = (
        flags.kubeconfig or os.getenv('KUBECONFIG') or '~/.kube/config')

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

    processor = KubeconfigProcessor()
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
    """Get the GKE Connect namespace by label.

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
