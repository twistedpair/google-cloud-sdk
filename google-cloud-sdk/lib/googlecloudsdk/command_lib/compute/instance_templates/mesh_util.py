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

import collections
import io
import json
import re

from googlecloudsdk.api_lib.container import util as c_util
from googlecloudsdk.command_lib.compute.instance_templates import service_proxy_aux_data
from googlecloudsdk.command_lib.container.hub import api_util
from googlecloudsdk.command_lib.container.hub import kube_util as hub_kube_util
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import yaml
from googlecloudsdk.core.util import files

EXPANSION_GATEWAY_NAME = 'istio-eastwestgateway'
SERVICE_PROXY_BUCKET_NAME = (
    'gs://gce-service-proxy/service-proxy-agent/releases/'
    'service-proxy-agent-asm-{}-stable.tgz')

ISTIO_CANONICAL_SERVICE_NAME_LABEL = 'service.istio.io/canonical-name'
ISTIO_CANONICAL_SERVICE_REVISION_LABEL = 'service.istio.io/canonical-revision'
KUBERNETES_APP_NAME_LABEL = 'app.kubernetes.io/name'
KUBERNETES_APP_VERSION_LABEL = 'app.kubernetes.io/version'

ISTIO_DISCOVERY_PORT = '15012'


def ParseWorkload(workload):
  """Parses the workload value to workload namespace and name.

  Args:
    workload: The workload value with namespace/name format.

  Returns:
    workload namespace and workload name.

  Raises:
    Error: if the workload value is invalid.
  """
  workload_pattern = r'(.*)\/(.*)'
  workload_match = re.search(workload_pattern, workload)
  if workload_match:
    return workload_match.group(1), workload_match.group(2)
  raise exceptions.Error(
      'value workload: {} is invalid. Workload value should have the format'
      'namespace/name.'.format(workload))


def ParseMembershipName(owner_id):
  """Get membership name from an owner id value.

  Args:
    owner_id: The owner ID value of a membership. e.g.,
    //gkehub.googleapis.com/projects/123/locations/global/memberships/test.

  Returns:
    The full resource name of the membership, e.g.,
      projects/foo/locations/global/memberships/name.

  Raises:
    Error: if the membership name cannot be parsed.
  """
  # Allow non-prod GKE Hub memberships to be specified.
  gkehub_pattern = r'\/\/gkehub(.*).googleapis.com\/(.*)'
  membership_match = re.search(gkehub_pattern, owner_id)
  if membership_match:
    return membership_match.group(2)
  raise exceptions.Error(
      'value owner_id: {} is invalid.'.format(owner_id))


def GetVMIdentityProvider(membership_manifest, workload_namespace):
  """Get the identity provider for the VMs.

  Args:
    membership_manifest: The membership manifest from the cluster.
    workload_namespace: The namespace of the VM workload.

  Returns:
    The identity provider value to be used on the VM connected to the cluster.

  Raises:
    ClusterError: If the membership manifest cannot be read.
  """
  if not membership_manifest:
    raise ClusterError('Cannot verify an empty membership from the cluster')

  try:
    membership_data = yaml.load(membership_manifest)
  except yaml.Error as e:
    raise exceptions.Error(
        'Invalid membership from the cluster {}'.format(membership_manifest), e)

  owner_id = GetNestedKeyFromManifest(
      membership_data, 'spec', 'owner', 'id')
  if not owner_id:
    raise ClusterError('Invalid membership does not have an owner id. Please '
                       'make sure your cluster is correctly registered and '
                       'retry.')

  membership_name = ParseMembershipName(owner_id)
  membership = api_util.GetMembership(membership_name)
  if not membership.uniqueId:
    raise exceptions.Error('Invalid membership {} does not have a unique_Id '
                           'field. Please make sure your cluster is correctly '
                           'registered and retry.'.format(membership_name))

  return '{}@google@{}'.format(membership.uniqueId, workload_namespace)


def RetrieveProxyConfig(mesh_config):
  """Retrieve proxy config from a mesh config.

  Args:
    mesh_config: A mesh config from the cluster.

  Returns:
    proxy_config: The proxy config from the mesh config.
  """
  try:
    proxy_config = mesh_config['defaultConfig']
  except KeyError:
    raise exceptions.Error(
        'Proxy config cannot be found in the Anthos Service Mesh.')

  return proxy_config


def RetrieveTrustDomain(mesh_config):
  """Retrieve trust domain from a mesh config.

  Args:
    mesh_config: A mesh config from the cluster.

  Returns:
    trust_domain: The trust domain from the mesh config.
  """
  try:
    trust_domain = mesh_config['trustDomain']
  except KeyError:
    raise exceptions.Error(
        'Trust Domain cannot be found in the Anthos Service Mesh.')

  return trust_domain


def RetrieveMeshId(mesh_config):
  """Retrieve mesh id from a mesh config.

  Args:
    mesh_config: A mesh config from the cluster.

  Returns:
    mesh_id: The mesh id from the mesh config.
  """
  proxy_config = RetrieveProxyConfig(mesh_config)

  try:
    mesh_id = proxy_config['meshId']
  except KeyError:
    raise exceptions.Error(
        'Mesh ID cannot be found in the Anthos Service Mesh.')

  return mesh_id


def GetWorkloadLabels(workload_manifest):
  """Get the workload labels from a workload manifest.

  Args:
    workload_manifest: The manifest of the workload.

  Returns:
    The workload labels.

  Raises:
    WorkloadError: If the workload manifest cannot be read.
  """
  if not workload_manifest:
    raise WorkloadError('Cannot verify an empty workload from the cluster')

  try:
    workload_data = yaml.load(workload_manifest)
  except yaml.Error as e:
    raise exceptions.Error(
        'Invalid workload from the cluster {}'.format(workload_data), e)

  workload_labels = GetNestedKeyFromManifest(workload_data, 'spec', 'metadata',
                                             'labels')

  return workload_labels


def GetCanonicalServiceName(workload_name, workload_manifest):
  """Get the canonical service name of the workload.

  Args:
    workload_name: The name of the workload.
    workload_manifest: The manifest of the workload.

  Returns:
    The canonical service name of the workload.
  """
  workload_labels = GetWorkloadLabels(workload_manifest)

  return ExtractCanonicalServiceName(workload_labels, workload_name)


def GetCanonicalServiceRevision(workload_manifest):
  """Get the canonical service revision of the workload.

  Args:
    workload_manifest: The manifest of the workload.

  Returns:
    The canonical service revision of the workload.
  """
  workload_labels = GetWorkloadLabels(workload_manifest)

  return ExtractCanonicalServiceRevision(workload_labels)


def ExtractCanonicalServiceName(workload_labels, workload_name):
  """Get the canonical service name of the workload.

  Args:
    workload_labels: A map of workload labels.
    workload_name: The name of the workload.

  Returns:
    The canonical service name of the workload.
  """
  if not workload_labels:
    return workload_name

  svc = workload_labels.get(ISTIO_CANONICAL_SERVICE_NAME_LABEL)
  if svc:
    return svc

  svc = workload_labels.get(KUBERNETES_APP_NAME_LABEL)
  if svc:
    return svc

  svc = workload_labels.get('app')
  if svc:
    return svc

  return workload_name


def ExtractCanonicalServiceRevision(workload_labels):
  """Get the canonical service revision of the workload.

  Args:
    workload_labels: A map of workload labels.

  Returns:
    The canonical service revision of the workload.
  """
  if not workload_labels:
    return 'latest'

  rev = workload_labels.get(ISTIO_CANONICAL_SERVICE_REVISION_LABEL)
  if rev:
    return rev

  rev = workload_labels.get(KUBERNETES_APP_VERSION_LABEL)
  if rev:
    return rev

  rev = workload_labels.get('version')
  if rev:
    return rev

  return 'latest'


def VerifyWorkloadSetup(workload_manifest):
  """Verify VM workload setup in the cluster."""
  if not workload_manifest:
    raise WorkloadError('Cannot verify an empty workload from the cluster')

  try:
    workload_data = yaml.load(workload_manifest)
  except yaml.Error as e:
    raise exceptions.Error(
        'Invalid workload from the cluster {}'.format(workload_manifest), e)

  identity_provider_value = GetNestedKeyFromManifest(
      workload_data, 'spec', 'metadata', 'annotations',
      'security.cloud.google.com/IdentityProvider')
  if identity_provider_value != 'google':
    raise WorkloadError('Unable to find the GCE IdentityProvider in the '
                        'specified WorkloadGroup. Please make sure the '
                        'GCE IdentityProvider is specified in the '
                        'WorkloadGroup.')


def RetrieveWorkloadRevision(namespace_manifest):
  """Retrieve the Anthos Service Mesh revision for the workload."""
  if not namespace_manifest:
    raise WorkloadError('Cannot verify an empty namespace from the cluster')

  try:
    namespace_data = yaml.load(namespace_manifest)
  except yaml.Error as e:
    raise exceptions.Error(
        'Invalid namespace from the cluster {}'.format(namespace_manifest), e)

  workload_revision = GetNestedKeyFromManifest(namespace_data, 'metadata',
                                               'labels', 'istio.io/rev')
  if not workload_revision:
    raise WorkloadError('Workload namespace does not have an Anthos Service '
                        'Mesh revision label. Please make sure the namespace '
                        'is labeled and try again.')

  return workload_revision


def RetrieveWorkloadServiceAccount(workload_manifest):
  """Retrieve the service account used for the workload."""
  if not workload_manifest:
    raise WorkloadError('Cannot verify an empty workload from the cluster')

  try:
    workload_data = yaml.load(workload_manifest)
  except yaml.Error as e:
    raise exceptions.Error(
        'Invalid workload from the cluster {}'.format(workload_manifest), e)

  service_account = GetNestedKeyFromManifest(workload_data, 'spec', 'template',
                                             'serviceAccount')
  return service_account


def ConfigureInstanceTemplate(args, kube_client, project_id, network_resource,
                              workload_namespace, workload_name,
                              workload_manifest, namespace_manifest,
                              membership_manifest, expansionagateway_ip,
                              root_cert):
  """Configure the provided instance template args with ASM metadata."""
  identity_provider = GetVMIdentityProvider(membership_manifest,
                                            workload_namespace)

  asm_revision = RetrieveWorkloadRevision(namespace_manifest)

  service_account = RetrieveWorkloadServiceAccount(workload_manifest)

  asm_version = kube_client.RetrieveASMVersion(asm_revision)

  mesh_config = kube_client.RetrieveMeshConfig(asm_revision)

  asm_proxy_config = RetrieveProxyConfig(mesh_config)

  trust_domain = RetrieveTrustDomain(mesh_config)

  mesh_id = RetrieveMeshId(mesh_config)

  network = network_resource.split('/')[-1]

  canonical_service = GetCanonicalServiceName(workload_name, workload_manifest)

  canonical_revision = GetCanonicalServiceRevision(workload_manifest)

  asm_labels = GetWorkloadLabels(workload_manifest)
  if asm_labels is None:
    asm_labels = collections.OrderedDict()

  asm_labels[ISTIO_CANONICAL_SERVICE_NAME_LABEL] = canonical_service
  asm_labels[ISTIO_CANONICAL_SERVICE_REVISION_LABEL] = canonical_revision

  asm_labels_string = json.dumps(asm_labels)

  service_proxy_config = collections.OrderedDict()
  service_proxy_config['mode'] = 'ON'
  service_proxy_config['proxy-spec'] = {
      'network': network,
      'api-server': '{}:{}'.format(expansionagateway_ip, ISTIO_DISCOVERY_PORT),
      'log-level': 'info',
  }
  service_proxy_config['service'] = {}

  if 'proxyMetadata' not in asm_proxy_config:
    asm_proxy_config['proxyMetadata'] = {}

  proxy_metadata = asm_proxy_config['proxyMetadata']
  proxy_metadata['ISTIO_META_WORKLOAD_NAME'] = workload_name
  proxy_metadata['ISTIO_META_ISTIO_VERSION'] = asm_version
  proxy_metadata['POD_NAMESPACE'] = workload_namespace
  proxy_metadata['USE_TOKEN_FOR_CSR'] = 'true'
  proxy_metadata['ISTIO_META_DNS_CAPTURE'] = 'true'
  proxy_metadata['ISTIO_META_AUTO_REGISTER_GROUP'] = workload_name
  proxy_metadata['SERVICE_ACCOUNT'] = service_account
  proxy_metadata['CREDENTIAL_IDENTITY_PROVIDER'] = identity_provider
  proxy_metadata['ASM_REVISION'] = asm_revision
  proxy_metadata['TRUST_DOMAIN'] = trust_domain
  proxy_metadata['ISTIO_META_MESH_ID'] = mesh_id
  proxy_metadata['ISTIO_META_NETWORK'] = '{}-{}'.format(project_id, network)
  proxy_metadata['CANONICAL_SERVICE'] = canonical_service
  proxy_metadata['CANONICAL_REVISION'] = canonical_revision
  proxy_metadata['ISTIO_METAJSON_LABELS'] = asm_labels_string

  service_proxy_config['asm-config'] = asm_proxy_config

  gce_software_declaration = collections.OrderedDict()
  service_proxy_agent_recipe = collections.OrderedDict()

  service_proxy_agent_recipe['name'] = 'install-gce-service-proxy-agent'
  service_proxy_agent_recipe['desired_state'] = 'INSTALLED'

  service_proxy_agent_recipe['installSteps'] = [{
      'scriptRun': {
          'script':
              service_proxy_aux_data.startup_script_for_asm_service_proxy
              .format(
                  ingress_ip=expansionagateway_ip, asm_revision=asm_revision)
      }
  }]

  gce_software_declaration['softwareRecipes'] = [service_proxy_agent_recipe]

  args.metadata['gce-software-declaration'] = json.dumps(
      gce_software_declaration)

  args.metadata['rootcert'] = root_cert
  if 'gce-service-proxy-agent-bucket' not in args.metadata:
    args.metadata[
        'gce-service-proxy-agent-bucket'] = SERVICE_PROXY_BUCKET_NAME.format(
            asm_version)
  args.metadata['enable-osconfig'] = 'true'
  args.metadata['enable-guest-attributes'] = 'true'
  args.metadata['gce-service-proxy'] = json.dumps(service_proxy_config)

  if args.labels is None:
    args.labels = collections.OrderedDict()
  args.labels['asm_service_name'] = canonical_service
  args.labels['asm_service_namespace'] = workload_namespace
  args.labels['mesh_id'] = mesh_id
  # For ASM VM usage tracking.
  args.labels['gce-service-proxy'] = 'asm-istiod'


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

  def GetNamespace(self, namespace):
    """Get the YAML output of the specified namespace."""
    out, err = self._RunKubectl([
        'get', 'namespace', namespace, '-o', 'yaml'], None)
    if err:
      raise exceptions.Error(
          'Error retrieving Namespace {}: {}'.format(namespace, err))
    return out

  def GetMembershipCR(self):
    """Get the YAML output of the Membership CR."""
    if not self._MembershipCRDExists():
      raise ClusterError(
          'Membership CRD is not found in the cluster. Please make sure your '
          'cluster is registered and retry.')

    out, err = self._RunKubectl(
        ['get',
         'memberships.hub.gke.io',
         'membership', '-o', 'yaml'], None)
    if err:
      if 'NotFound' in err:
        raise ClusterError(
            'The specified cluster is not registered to a fleet. '
            'Please make sure your cluster is registered and retry.')
      raise exceptions.Error(
          'Error retrieving the Membership CR: {}'.format(err))
    return out

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

  def GetIdentityProviderCR(self):
    """Get the YAML output of the IdentityProvider CR."""
    if not self._IdentityProviderCRDExists():
      raise ClusterError(
          'IdentityProvider CRD is not found in the cluster. Please install '
          'Anthos Service Mesh with VM support and retry.')

    out, err = self._RunKubectl(
        ['get',
         'identityproviders.security.cloud.google.com',
         'google', '-o', 'yaml'], None)
    if err:
      if 'NotFound' in err:
        raise ClusterError(
            'GCE identity provider is not found in the cluster. '
            'Please install Anthos Service Mesh with VM support.')
      raise exceptions.Error(
          'Error retrieving IdentityProvider google in default namespace: {}'
          .format(err))
    return out

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
      raise ClusterError(
          'WorkloadGroup CRD is not found in the cluster. Please install '
          'Anthos Service Mesh and retry.')

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
              workload_name, workload_namespace, err))
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

  def RetrieveExpansionGatewayIP(self):
    """Retrieves the expansion gateway IP from the cluster."""
    if not self.ExpansionGatewayDeploymentExists():
      raise ClusterError(
          'The gateway {} deployment is not found in the cluster. Please '
          'install Anthos Service Mesh with VM support and retry.'.format(
              EXPANSION_GATEWAY_NAME))

    if not self.ExpansionGatewayServiceExists():
      raise ClusterError(
          'The gateway {} service is not found in the cluster. Please '
          'install Anthos Service Mesh with VM support and retry.'.format(
              EXPANSION_GATEWAY_NAME))

    out, err = self._RunKubectl([
        'get', 'svc', EXPANSION_GATEWAY_NAME, '-n', 'istio-system', '-o',
        'jsonpath={.status.loadBalancer.ingress[0].ip}'
    ], None)
    if err:
      raise exceptions.Error(
          'Error retrieving expansion gateway IP: {}'.format(err))
    return out

  def RetrieveKubernetesRootCert(self):
    """Retrieves the root cert from the cluster."""
    out, err = self._RunKubectl(
        ['get', 'configmap', 'kube-root-ca.crt', '-o',
         r'jsonpath="{.data.ca\.crt}"'], None)
    if err:
      if 'NotFound' in err:
        raise ClusterError(
            'Cluster root certificate is not found.')
      raise exceptions.Error(
          'Error retrieving Kubernetes root cert: {}'.format(err))
    return out.strip('\"')

  def RetrieveASMVersion(self, revision):
    """Retrieves the version of ASM."""
    image, err = self._RunKubectl([
        'get', 'deploy', '-l', 'istio.io/rev={},app=istiod'.format(revision),
        '-n', 'istio-system', '-o',
        'jsonpath="{.items[0].spec.template.spec.containers[0].image}"'
    ], None)
    if err:
      if 'NotFound' in err:
        return None
      raise exceptions.Error(
          'Error retrieving Anthos Service Mesh version: {}'.format(err))

    if not image:
      raise ClusterError('Anthos Service Mesh revision {} is not found in the '
                         'cluster. Please install Anthos Service Mesh and try '
                         'again.'.format(revision))

    asm_version_pattern = r':(.*)-'
    version_match = re.search(asm_version_pattern, image)
    if version_match:
      return version_match.group(1)
    raise exceptions.Error(
        'Value image: {} is invalid.'.format(image))

  def RetrieveMeshConfig(self, revision):
    """Retrieves the MeshConfig for the ASM revision."""
    out, err = self._RunKubectl(
        ['get', 'configmap', 'istio-{}'.format(revision), '-n', 'istio-system',
         '-o', 'jsonpath={.data.mesh}'], None)
    if err:
      if 'NotFound' in err:
        return None
      raise exceptions.Error(
          'Error retrieving the mesh config from the cluster: {}'.format(
              err))

    try:
      mesh_config = yaml.load(out)
    except yaml.Error as e:
      raise exceptions.Error(
          'Invalid mesh config from the cluster {}'.format(out), e)

    return mesh_config

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
