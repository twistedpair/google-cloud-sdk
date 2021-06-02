# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Utils for mesh flag in the instance template commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import re

from googlecloudsdk.api_lib.container import util as c_util
from googlecloudsdk.command_lib.container.hub import kube_util as hub_kube_util
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import yaml
from googlecloudsdk.core.util import files

EXPANSION_GATEWAY_NAME = 'istio-eastwestgateway'


def ParseWorkload(workload):
  """Parses the workload value to workload namespace and name.

  Args:
    workload: The workload value with namespace/name format.

  Returns:
    workload namespace and workload name.

  Raises:
    Error: if the workload value is invalid.
  """
  rgx = r'(.*)\/(.*)'
  workload_matcher = re.search(rgx, workload)
  if workload_matcher is not None:
    return workload_matcher.group(1), workload_matcher.group(2)
  raise exceptions.Error(
      'value workload: {} is invalid. Workload value should have the format'
      'namespace/name.'.format(workload))


def VerifyClusterSetup(kube_client):
  """Verify cluster prerequisites for adding VMs to the mesh."""
  # When deciding cluster registration, only checking the membership CR to avoid
  # Hub permissions being required.
  if not kube_client.MembershipCRExists():
    raise ClusterError('The specified cluster is not registered to an environ. '
                       'Please make sure your cluster is registered and retry.')
  if not kube_client.IdentityProviderCRExists():
    raise ClusterError('GCE identity provider is not found in the cluster. '
                       'Please install Anthos Service Mesh with VM support.')
  VerifyExpansionGateway(kube_client)


def VerifyWorkloadSetup(kube_client, workload_manifest):
  """Verify VM workload setup in the cluster."""
  if not workload_manifest:
    raise WorkloadError('Cannot verify an empty workload from the cluster')

  try:
    workload_data = yaml.load(workload_manifest)
  except yaml.Error as e:
    raise exceptions.Error(
        'Invalid workload from the cluster {}'.format(workload_data), e)

  identity_provider_value = GetNestedKeyFromManifest(
      workload_data, 'spec', 'metadata', 'annotations',
      'security.cloud.google.com/IdentityProvider')
  if identity_provider_value != 'google':
    raise WorkloadError('Unable to find the GCE IdentityProvider in the '
                        'specified WorkloadGroup. Please make sure the '
                        'GCE IdentityProvider is specified in the '
                        'WorkloadGroup.')


def VerifyExpansionGateway(kube_client):
  """Verify the ASM expansion gateway installation in the cluster."""
  if not kube_client.ExpansionGatewayServiceExists(
  ) or not kube_client.ExpansionGatewayDeploymentExists():
    raise ClusterError('The gateway {} is not found in the cluster. Please '
                       'install Anthos Service Mesh with VM support.'.format(
                           EXPANSION_GATEWAY_NAME))


class KubernetesClient(object):
  """Kubernetes client for access Kubernetes APIs."""

  def __init__(self, gke_cluster=None):
    """KubernetesClient constructor.

    Args:
      gke_cluster: the location/name of the GKE cluster.
    """
    self.kubectl_timeout = '20s'

    self.temp_kubeconfig_dir = files.TemporaryDirectory()
    self.processor = hub_kube_util.KubeconfigProcessor(
        gke_uri=None, gke_cluster=gke_cluster, kubeconfig=None, context=None)
    self.kubeconfig, self.context = self.processor.GetKubeconfigAndContext(
        self.temp_kubeconfig_dir)

  def __enter__(self):
    return self

  def __exit__(self, *_):
    # delete temp directory
    if self.temp_kubeconfig_dir is not None:
      self.temp_kubeconfig_dir.Close()

  def HasNamespaceReaderPermissions(self, *namespaces):
    """Check to see if the user has read permissions in the namespaces.

    Args:
      *namespaces: The namespaces to verify reader permissions.

    Returns:
      true, if reads can be performed on all of the specified namespaces.

    Raises:
      Error: if failing to get check for read permissions.
      Error: if read permissions are not found.
    """
    for ns in namespaces:
      out, err = self._RunKubectl(
          ['auth', 'can-i', 'read', '*', '-n', ns], None)
      if err:
        raise exceptions.Error(
            'Failed to check if the user can read resources in {} namespace: {}'
            .format(ns, err))
      if 'yes' not in out:
        raise exceptions.Error(
            'Missing permissions to read resources in {} namespace'.format(ns))
    return True

  def NamespacesExist(self, *namespaces):
    """Check to see if the namespaces exist in the cluster.

    Args:
      *namespaces: The namespaces to check.

    Returns:
      true, if namespaces exist.

    Raises:
      Error: if failing to verify the namespaces.
      Error: if at least one of the namespaces do not exist.
    """
    for ns in namespaces:
      _, err = self._RunKubectl(['get', 'namespace', ns], None)
      if err:
        if 'NotFound' in err:
          raise exceptions.Error('Namespace {} does not exist: {}'.format(
              ns, err))
        raise exceptions.Error(
            'Failed to check if namespace {} exists: {}'.format(ns, err))
    return True

  def MembershipCRExists(self):
    """Verifies if GKE Hub membership CR exists."""
    if not self._MembershipCRDExists():
      return None

    _, err = self._RunKubectl(
        ['get',
         'memberships.hub.gke.io',
         'membership'], None)
    if err:
      if 'NotFound' in err:
        return False
      raise exceptions.Error(
          'Error retrieving the Membership CR: {}'.format(err))
    return True

  def _MembershipCRDExists(self):
    """Verifies if GKE Hub membership CRD exists."""
    _, err = self._RunKubectl(
        ['get',
         'customresourcedefinitions.v1.apiextensions.k8s.io',
         'memberships.hub.gke.io'], None)
    if err:
      if 'NotFound' in err:
        return False
      raise exceptions.Error(
          'Error retrieving the Membership CRD: {}'.format(err))
    return True

  def IdentityProviderCRExists(self):
    """Verifies if the google Identity Provider CR exists."""
    if not self._IdentityProviderCRDExists():
      return None

    _, err = self._RunKubectl(
        ['get',
         'identityproviders.security.cloud.google.com',
         'google'], None)
    if err:
      if 'NotFound' in err:
        return False
      raise exceptions.Error(
          'Error retrieving the google Identity Provider CR: {}'.format(err))
    return True

  def _IdentityProviderCRDExists(self):
    """Verifies if Identity Provider CRD exists."""
    _, err = self._RunKubectl(
        ['get',
         'customresourcedefinitions.v1.apiextensions.k8s.io',
         'identityproviders.security.cloud.google.com'], None)
    if err:
      if 'NotFound' in err:
        return False
      raise exceptions.Error(
          'Error retrieving the Identity Provider CRD: {}'.format(err))
    return True

  def GetWorkloadGroupCR(self, workload_namespace, workload_name):
    """Get the YAML output of the specified WorkloadGroup CR."""
    if not self._WorkloadGroupCRDExists():
      return None

    out, err = self._RunKubectl([
        'get', 'workloadgroups.networking.istio.io', workload_name, '-n',
        workload_namespace, '-o', 'yaml'
    ], None)
    if err:
      if 'NotFound' in err:
        raise WorkloadError(
            'WorkloadGroup {} in namespace {} is not found in the '
            'cluster. Please create the WorkloadGroup and retry.'.format(
                workload_name, workload_namespace))
      raise exceptions.Error(
          'Error retrieving WorkloadGroup {} in namespace {}: {}'.format(
              err, workload_name, workload_namespace))
    return out

  def _WorkloadGroupCRDExists(self):
    """Verifies if WorkloadGroup CRD exists."""
    _, err = self._RunKubectl(
        ['get',
         'customresourcedefinitions.v1.apiextensions.k8s.io',
         'workloadgroups.networking.istio.io'], None)
    if err:
      if 'NotFound' in err:
        return False
      raise exceptions.Error(
          'Error retrieving the WorkloadGroup CRD: {}'.format(err))
    return True

  def ExpansionGatewayDeploymentExists(self):
    """Verifies if the ASM Expansion Gateway deployment exists."""
    _, err = self._RunKubectl(
        ['get', 'deploy', EXPANSION_GATEWAY_NAME, '-n', 'istio-system'], None)
    if err:
      if 'NotFound' in err:
        return False
      raise exceptions.Error(
          'Error retrieving the expansion gateway deployment: {}'.format(err))
    return True

  def ExpansionGatewayServiceExists(self):
    """Verifies if the ASM Expansion Gateway service exists."""
    _, err = self._RunKubectl(
        ['get', 'service', EXPANSION_GATEWAY_NAME, '-n', 'istio-system'], None)
    if err:
      if 'NotFound' in err:
        return False
      raise exceptions.Error(
          'Error retrieving the expansion gateway service: {}'.format(err))
    return True

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


def GetNestedKeyFromManifest(manifest, *keys):
  """Get the value of a key path from a dict.

  Args:
    manifest: the dict representation of a manifest
    *keys: an ordered list of items in the nested key

  Returns:
    The value of the nested key in the manifest. None, if the nested key does
    not exist.
  """
  for key in keys:
    if not isinstance(manifest, dict):
      return None
    try:
      manifest = manifest[key]
    except KeyError:
      return None
  return manifest


class PermissionsError(exceptions.Error):
  """Class for errors raised when verifying permissions."""


class ClusterError(exceptions.Error):
  """Class for errors raised when verifying cluster setup."""


class WorkloadError(exceptions.Error):
  """Class for errors raised when verifying workload setup."""
