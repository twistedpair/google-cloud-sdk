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
from googlecloudsdk.core.util import files


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
         'customresourcedefinitions.v1beta1.apiextensions.k8s.io',
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
         'customresourcedefinitions.v1beta1.apiextensions.k8s.io',
         'identityproviders.security.cloud.google.com'], None)
    if err:
      if 'NotFound' in err:
        return False
      raise exceptions.Error(
          'Error retrieving the Identity Provider CRD: {}'.format(err))
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


class PermissionsError(exceptions.Error):
  """Class for errors raised when verifying permissions."""


class ClusterError(exceptions.Error):
  """Class for errors raised when verifying cluster setup."""
