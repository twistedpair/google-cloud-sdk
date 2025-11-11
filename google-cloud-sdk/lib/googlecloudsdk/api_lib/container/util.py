# -*- coding: utf-8 -*- #
# Copyright 2014 Google LLC. All Rights Reserved.
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
"""Common utilities for the containers tool."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import os
import re

from apitools.base.py import encoding
from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.container import kubeconfig as kconfig
from googlecloudsdk.api_lib.services import enable_api
from googlecloudsdk.api_lib.services import exceptions
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.core import config
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import yaml
from googlecloudsdk.core.credentials import store as c_store
from googlecloudsdk.core.resource import resource_printer
from googlecloudsdk.core.updater import update_manager
from googlecloudsdk.core.util import files as file_utils
from googlecloudsdk.core.util import platforms
import six

CLUSTERS_FORMAT = """
    table(
        name,
        zone:label=LOCATION,
        master_version():label=MASTER_VERSION,
        endpoint:label=MASTER_IP,
        nodePools[0].config.machineType,
        currentNodeVersion:label=NODE_VERSION,
        firstof(currentNodeCount,initialNodeCount):label=NUM_NODES,
        status,
        ipAllocationPolicy.stackType.yesno(no='IPV4'):label=STACK_TYPE
    )
"""

OPERATIONS_FORMAT = """
    table(
        name,
        operationType:label=TYPE,
        zone:label=LOCATION,
        targetLink.basename():label=TARGET,
        statusMessage,
        status,
        startTime,
        endTime
    )
"""

NODEPOOLS_FORMAT = """
     table(
        name,
        config.machineType,
        config.diskSizeGb,
        version:label=NODE_VERSION
     )
"""

HTTP_ERROR_FORMAT = (
    'ResponseError: code={status_code}, message={status_message}'
)

WARN_NODE_VERSION_WITH_AUTOUPGRADE_ENABLED = (
    'Node version is specified while node auto-upgrade is enabled. '
    'Node-pools created at the specified version will be auto-upgraded '
    'whenever auto-upgrade preconditions are met.'
)

WARN_BETA_APIS_ENABLED = (
    ' Kubernetes Beta APIs are not stable, it is advised to use them with'
    ' caution. Please read carefully about limitations and associated risks at'
    ' https://cloud.google.com//kubernetes-engine/docs/how-to/use-beta-apis '
)

INVALIID_SURGE_UPGRADE_SETTINGS = (
    "'--max-surge-upgrade' and '--max-unavailable-upgrade' must be used in "
    'conjunction.'
)

INVALID_NC_FLAG_CONFIG_OVERLAP = (
    'insecureKubeletReadonlyPortEnabled specified in both config '
    'file and by flag. Please specify either command line option '
    'or the value in the config file.'
)


GKE_DEFAULT_POD_RANGE = 14
GKE_DEFAULT_POD_RANGE_PER_NODE = 24
GKE_ROUTE_BASED_SERVICE_RANGE = 20

NC_KUBELET_CONFIG = 'kubeletConfig'
NC_CPU_MANAGER_POLICY = 'cpuManagerPolicy'
NC_CPU_CFS_QUOTA = 'cpuCFSQuota'
NC_CPU_CFS_QUOTA_PERIOD = 'cpuCFSQuotaPeriod'
NC_POD_PIDS_LIMIT = 'podPidsLimit'
NC_KUBELET_READONLY_PORT = 'insecureKubeletReadonlyPortEnabled'
NC_ALLOWED_UNSAFE_SYSCTLS = 'allowedUnsafeSysctls'
NC_CONTAINER_LOG_MAX_SIZE = 'containerLogMaxSize'
NC_CONTAINER_LOG_MAX_FILES = 'containerLogMaxFiles'
NC_IMAGE_GC_HIGH_THRESHOLD_PERCENT = 'imageGcHighThresholdPercent'
NC_IMAGE_GC_LOW_THRESHOLD_PERCENT = 'imageGcLowThresholdPercent'
NC_IMAGE_MINIMUM_GC_AGE = 'imageMinimumGcAge'
NC_IMAGE_MAXIMUM_GC_AGE = 'imageMaximumGcAge'
NC_NODE_SWAP_SIZE_GIB = 'nodeSwapSizeGib'
NC_MAX_PARALLEL_IMAGE_PULLS = 'maxParallelImagePulls'
NC_LINUX_CONFIG = 'linuxConfig'
NC_SYSCTL = 'sysctl'
NC_CGROUP_MODE = 'cgroupMode'
NC_TRANSPARENT_HUGEPAGE_ENABLED = 'transparentHugepageEnabled'
NC_TRANSPARENT_HUGEPAGE_DEFRAG = 'transparentHugepageDefrag'
NC_HUGEPAGE = 'hugepageConfig'
NC_HUGEPAGE_2M = 'hugepage_size2m'
NC_HUGEPAGE_1G = 'hugepage_size1g'
NC_MEMORY_MANAGER = 'memoryManager'
NC_MEMORY_MANAGER_POLICY = 'policy'
NC_TOPOLOGY_MANAGER = 'topologyManager'
NC_TOPOLOGY_MANAGER_POLICY = 'policy'
NC_TOPOLOGY_MANAGER_SCOPE = 'scope'
NC_SINGLE_PROCESS_OOMKILL = 'singleProcessOomKill'
NC_KERNEL_OVERRIDES = 'kernelOverrides'
NC_KERNEL_COMMANDLINE_OVERRIDES = 'kernelCommandlineOverrides'
NC_KERNEL_SPEC_RSTACK_OVERFLOW = 'specRstackOverflow'
NC_KERNEL_INIT_ON_ALLOC = 'initOnAlloc'
NC_LRU_GEN = 'lruGen'
NC_LRU_GEN_ENABLED = 'enabled'
NC_LRU_GEN_MIN_TTL_MS = 'minTtlMs'

NC_ADDITIONAL_ETC_HOSTS = 'additionalEtcHosts'
NC_ADDITIONAL_ETC_SYSTEMD_RESOLVED_CONF = 'additionalEtcSystemdResolvedConf'
NC_ADDITIONAL_ETC_RESOLV_CONF = 'additionalEtcResolvConf'
NC_TIME_ZONE = 'timeZone'
NC_CUSTOM_NODE_INIT = 'customNodeInit'
NC_CUSTOM_NODE_INIT_SCRIPT = 'initScript'
NC_CUSTOM_NODE_INIT_SCRIPT_GCS_URI = 'gcsUri'
NC_CUSTOM_NODE_INIT_SCRIPT_GCS_GENERATION = 'gcsGeneration'
NC_CUSTOM_NODE_INIT_SCRIPT_ARGS = 'args'
NC_ETC_HOSTS_ENTRY_IP = 'ip'
NC_ETC_HOSTS_ENTRY_HOST = 'host'
NC_RESOLVED_CONF_ENTRY_KEY = 'key'
NC_RESOLVED_CONF_ENTRY_VALUE = 'value'

NC_SWAP_CONFIG = 'swapConfig'
NC_SWAP_CONFIG_ENABLED = 'enabled'
NC_SWAP_CONFIG_ENCRYPTION_CONFIG = 'encryptionConfig'
NC_SWAP_CONFIG_ENCRYPTION_CONFIG_DISABLED = 'disabled'
NC_SWAP_CONFIG_BOOT_DISK_PROFILE = 'bootDiskProfile'
NC_SWAP_CONFIG_EPHEMERAL_LOCAL_SSD_PROFILE = 'ephemeralLocalSsdProfile'
NC_SWAP_CONFIG_DEDICATED_LOCAL_SSD_PROFILE = 'dedicatedLocalSsdProfile'
NC_SWAP_CONFIG_SWAP_SIZE_GIB = 'swapSizeGib'
NC_SWAP_CONFIG_SWAP_SIZE_PERCENT = 'swapSizePercent'
NC_SWAP_CONFIG_DISK_COUNT = 'diskCount'
NC_CC_PRIVATE_CR_CONFIG = 'privateRegistryAccessConfig'
NC_CC_PRIVATE_CR_CONFIG_ENABLED = 'enabled'
NC_CC_WRITABLE_CGROUPS = 'writableCgroups'
NC_CC_WRITABLE_CGROUPS_ENABLED = 'enabled'

NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS = 'registryHosts'
NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_SERVER = 'server'
NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_HOSTS = 'hosts'
NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_HOST = 'host'
NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_OVERRIDE_PATH = 'overridePath'
NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_HEADER = 'header'
NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_HEADER_KEY = 'key'
NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_HEADER_VALUE = 'value'
NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_DIAL_TIMEOUT = 'dialTimeout'
NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_CAPABILITIES = 'capabilities'
NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_GCP_SECRET_URI = (
    'gcpSecretManagerSecretUri'
)
NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_CA = 'ca'
NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_CLIENT = 'client'
NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_CLIENT_CERT = 'cert'
NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_CLIENT_KEY = 'key'

NC_CC_CA_CONFIG = 'certificateAuthorityDomainConfig'
NC_CC_GCP_SECRET_CONFIG = 'gcpSecretManagerCertificateConfig'
NC_CC_GCP_SECRET_CONFIG_SECRET_URI = 'secretURI'
NC_CC_PRIVATE_CR_FQDNS_CONFIG = 'fqdns'

NC_EVICTION_SOFT = 'evictionSoft'
NC_EVICTION_SOFT_GRACE_PERIOD = 'evictionSoftGracePeriod'
NC_EVICTION_MINIMUM_RECLAIM = 'evictionMinimumReclaim'
NC_EVICTION_MAX_POD_GRACE_PERIOD_SECONDS = 'evictionMaxPodGracePeriodSeconds'


class Error(core_exceptions.Error):
  """Class for errors raised by container commands."""


def ConstructList(title, items):
  buf = io.StringIO()
  resource_printer.Print(items, 'list[title="{0}"]'.format(title), out=buf)
  return buf.getvalue()


MISSING_KUBECTL_MSG = """\
Accessing a Kubernetes Engine cluster requires the kubernetes commandline
client [kubectl]. To install, run
  $ gcloud components install kubectl
"""

_KUBECTL_COMPONENT_NAME = 'kubectl'

CGROUPV1_DEPRECATED_MSG = (
    'CGROUP_MODE_V1 is deprecated. Please use CGROUP_MODE_V2 instead. '
    'For additional details, please refer to'
    ' https://cloud.google.com/kubernetes-engine/docs/how-to/migrate-cgroupv2'
)

CGROUPV1_NODEPOOLS_MSG = (
    'Node pool {0} is running cgroupv1 which is deprecated. Please use'
    ' cgroupv2 instead. For additional details, please refer to'
    ' https://cloud.google.com/kubernetes-engine/docs/how-to/migrate-cgroupv2'
)

CGROUPV1_CHECKING_FAILURE_MSG = (
    'Problem checking cgroup mode of node pools:\n\n{}\n\n'
    'Please make sure the node pools are running cgroupv2`.\n'
)


def _KubectlInstalledAsComponent():
  if config.Paths().sdk_root is not None:
    platform = platforms.Platform.Current()
    manager = update_manager.UpdateManager(platform_filter=platform, warn=False)
    installed_components = manager.GetCurrentVersionsInformation()
    return _KUBECTL_COMPONENT_NAME in installed_components


def CheckKubectlInstalled():
  """Verify that the kubectl component is installed or print a warning."""
  executable = file_utils.FindExecutableOnPath(_KUBECTL_COMPONENT_NAME)
  component = _KubectlInstalledAsComponent()
  if not (executable or component):
    log.warning(MISSING_KUBECTL_MSG)
    return None

  return executable if executable else component


def GenerateClusterUrl(cluster_ref):
  return (
      'https://console.cloud.google.com/kubernetes/'
      'workload_/gcloud/{location}/{cluster}?project={project}'
  ).format(
      location=cluster_ref.zone,
      cluster=cluster_ref.clusterId,
      project=cluster_ref.projectId,
  )


def _GetCrossConnectConfigItemFromSubnetwork(cluster, cross_connect_subnetwork):
  for item in cluster.privateClusterConfig.crossConnectConfig.items:
    if item.subnetwork == cross_connect_subnetwork:
      return item
  raise MissingCrossConnectError(cluster, cross_connect_subnetwork)


def _GetCrossConnectSubnetworkEndpoint(cluster, cross_connect_subnetwork):
  """Extract endpoint for the kubeconfig from the cross connect subnetwork."""
  cross_connect_config_item = _GetCrossConnectConfigItemFromSubnetwork(
      cluster, cross_connect_subnetwork
  )
  return cross_connect_config_item.privateEndpoint


def _GetFqdnPrivateEndpoint(cluster):
  """Extract endpoint for the kubeconfig from the fqdn."""
  fqdn = cluster.privateClusterConfig.privateEndpointFqdn
  if fqdn is None:
    raise MissingPrivateFqdnError(cluster)
  return fqdn


def LocationalResourceToZonal(path):
  """Converts a resource identifier (possibly a full URI) to the zonal format.

  e.g., container.projects.locations.clusters (like
  projects/foo/locations/us-moon1/clusters/my-cluster) ->
  container.projects.zones.clusters (like
  projects/foo/zones/us-moon1/clusters/my-cluster). While the locational format
  is newer, we have to use a single one because the formats have different
  fields. This allows either to be input, but the code will use entirely the
  zonal format.

  Args:
    path: A string resource name, possibly a URI (i.e., self link).

  Returns:
    The string identifier converted to zonal format if applicable. Unchanged if
    not applicable (i.e., not a full path or already in zonal format).
  """
  return path.replace('/locations/', '/zones/')


def _GetClusterEndpoint(
    cluster,
    use_internal_ip,
    cross_connect_subnetwork,
    use_private_fqdn,
    use_dns_endpoint,
):
  """Get the cluster endpoint suitable for writing to kubeconfig."""
  if (
      # TODO(b/365115169)
      cluster.controlPlaneEndpointsConfig is not None
      and cluster.controlPlaneEndpointsConfig.ipEndpointsConfig is not None
      and not cluster.controlPlaneEndpointsConfig.ipEndpointsConfig.enabled
  ) and (use_internal_ip or cross_connect_subnetwork or use_private_fqdn):
    raise IPEndpointsIsDisabledError(cluster)

  if (
      use_dns_endpoint
      and cluster.controlPlaneEndpointsConfig is not None
      and cluster.controlPlaneEndpointsConfig.dnsEndpointConfig is not None
      and not (
          cluster.controlPlaneEndpointsConfig.dnsEndpointConfig.allowExternalTraffic
      )
  ):
    if not _IsGoogleInternalUser():
      raise AllowExternalTrafficIsDisabledError(cluster)
    else:
      log.warning(
          'Retrieving DNS endpoint for internal user even though'
          ' allowExternalTraffic is disabled. Remove the --dns-endpoint flag if'
          ' this is not intended.'
      )

  if use_dns_endpoint or (
      # TODO(b/365115169)
      cluster.controlPlaneEndpointsConfig is not None
      and cluster.controlPlaneEndpointsConfig.ipEndpointsConfig is not None
      and not cluster.controlPlaneEndpointsConfig.ipEndpointsConfig.enabled
  ):
    return _GetDNSEndpoint(cluster)

  if use_internal_ip or cross_connect_subnetwork or use_private_fqdn:
    if not cluster.privateClusterConfig:
      raise NonPrivateClusterError(cluster)
    if not cluster.privateClusterConfig.privateEndpoint:
      raise MissingPrivateEndpointError(cluster)
    if cross_connect_subnetwork is not None:
      return _GetCrossConnectSubnetworkEndpoint(
          cluster, cross_connect_subnetwork
      )
    if use_private_fqdn:
      return _GetFqdnPrivateEndpoint(cluster)
    return cluster.privateClusterConfig.privateEndpoint

  if not cluster.endpoint:
    raise MissingEndpointError(cluster)
  return cluster.endpoint


def _GetDNSEndpoint(cluster):
  """Extract dns endpoint for the kubeconfig from the ControlPlaneEndpointConfig."""
  if (
      not cluster.controlPlaneEndpointsConfig
      or not cluster.controlPlaneEndpointsConfig.dnsEndpointConfig
      or not cluster.controlPlaneEndpointsConfig.dnsEndpointConfig.endpoint
  ):
    raise MissingDnsEndpointConfigError(cluster)
  dns_endpoint = cluster.controlPlaneEndpointsConfig.dnsEndpointConfig.endpoint
  if dns_endpoint is None:
    raise MissingDNSEndpointError(cluster)
  return dns_endpoint


KUBECONFIG_USAGE_FMT = """\
kubeconfig entry generated for {cluster}."""


class MissingPrivateFqdnError(Error):
  """Error for retrieving private fqdn of a cluster that has none."""

  def __init__(self, cluster):
    super(MissingPrivateFqdnError, self).__init__(
        'cluster {0} is missing private fqdn.'.format(cluster.name)
    )


class MissingDnsEndpointConfigError(Error):
  """Error for retrieving DNSEndpoint config of a cluster that has none."""

  def __init__(self, cluster):
    super(MissingDnsEndpointConfigError, self).__init__(
        'cluster {0} is missing DNSEndpointConfig.'.format(cluster.name)
    )


class MissingDNSEndpointError(Error):
  """Error for retrieving DNSEndpoint of a cluster that has none."""

  def __init__(self, cluster):
    super(MissingDNSEndpointError, self).__init__(
        'cluster {0} is missing DNSEndpoint.'.format(cluster.name)
    )


class MissingCrossConnectError(Error):
  """Error for retrieving cross-connect-subnet of a cluster that has none."""

  def __init__(self, cluster, cross_connect_subnet):
    super(MissingCrossConnectError, self).__init__(
        'cluster {0} is missing cross-connect subnetwork {1}.'.format(
            cluster.name, cross_connect_subnet
        )
    )


class MissingEndpointError(Error):
  """Error for attempting to persist a cluster that has no endpoint."""

  def __init__(self, cluster):
    super(MissingEndpointError, self).__init__(
        'cluster {0} is missing endpoint. Is it still PROVISIONING?'.format(
            cluster.name
        )
    )


class NonPrivateClusterError(Error):
  """Error for attempting to persist internal IP of a non-private cluster."""

  def __init__(self, cluster):
    super(NonPrivateClusterError, self).__init__(
        'cluster {0} is not a private cluster.'.format(cluster.name)
    )


class MissingPrivateEndpointError(Error):
  """Error for attempting to persist a cluster that has no internal IP."""

  def __init__(self, cluster):
    super(MissingPrivateEndpointError, self).__init__(
        'cluster {0} is missing private endpoint. Is it still '
        'PROVISIONING?'.format(cluster.name)
    )


class NodeConfigError(Error):
  """Error for attempting parse node config YAML/JSON file."""

  def __init__(self, e):
    super(NodeConfigError, self).__init__('Invalid node config: {0}'.format(e))


class AutoprovisioningConfigError(Error):
  """Error for attempting parse autoprovisioning config YAML/JSON file."""

  def __init__(self, e):
    super(AutoprovisioningConfigError, self).__init__(
        'Invalid autoprovisioning config file: {0}'.format(e)
    )


class IPEndpointsIsDisabledError(Error):
  """Error for attempting to persist internal IP for cluster with ipEndpoint access disabled."""

  def __init__(self, cluster):
    super(IPEndpointsIsDisabledError, self).__init__(
        'IP access is disabled for cluster {0}.'.format(cluster.name)
    )


class AllowExternalTrafficIsDisabledError(Error):
  """Error for attempting to persist DNS endpoint for cluster with allowExternalTraffic disabled."""

  def __init__(self, cluster):
    super(AllowExternalTrafficIsDisabledError, self).__init__(
        'controlPlaneEndpointsConfig.dnsEndpointConfig.allowExternalTraffic is'
        ' disabled for cluster {0}.'.format(cluster.name)
    )


class ClusterConfig(object):
  """Encapsulates persistent cluster config data.

  Call ClusterConfig.Load() or ClusterConfig.Persist() to create this
  object.
  """

  _CONFIG_DIR_FORMAT = '{project}_{zone}_{cluster}'

  KUBECONTEXT_FORMAT = 'gke_{project}_{zone}_{cluster}'

  def __init__(self, **kwargs):
    self.cluster_name = kwargs['cluster_name']
    self.zone_id = kwargs['zone_id']
    self.project_id = kwargs['project_id']
    self.server = kwargs['server']
    # auth options are auth-provider, or client certificate.
    self.auth_provider = kwargs.get('auth_provider')
    self.exec_auth = kwargs.get('exec_auth')
    self.ca_data = kwargs.get('ca_data')
    self.client_cert_data = kwargs.get('client_cert_data')
    self.client_key_data = kwargs.get('client_key_data')
    self.dns_endpoint = kwargs.get('dns_endpoint')
    self.impersonate_service_account = kwargs.get('impersonate_service_account')
    self.kubecontext_override = kwargs.get('kubecontext_override')
    self.use_iam_token = kwargs.get('use_iam_token')

  def __str__(self):
    return 'ClusterConfig{project:%s, cluster:%s, zone:%s}' % (
        self.project_id,
        self.cluster_name,
        self.zone_id,
    )

  def _Fullpath(self, filename):
    return os.path.abspath(os.path.join(self.config_dir, filename))

  @property
  def config_dir(self):
    return ClusterConfig.GetConfigDir(
        self.cluster_name, self.zone_id, self.project_id
    )

  @property
  def kube_context(self):
    return ClusterConfig.KubeContext(
        self.cluster_name,
        self.zone_id,
        self.project_id,
        self.kubecontext_override,
    )

  @property
  def has_cert_data(self):
    return bool(self.client_key_data and self.client_cert_data)

  @property
  def has_certs(self):
    return self.has_cert_data

  @property
  def has_ca_cert(self):
    return self.ca_data

  @property
  def has_dns_endpoint(self):
    return self.dns_endpoint

  @property
  def has_impersonate_service_account(self):
    return self.impersonate_service_account

  @staticmethod
  def UseGCPAuthProvider():
    return not properties.VALUES.container.use_client_certificate.GetBool()

  @staticmethod
  def GetConfigDir(cluster_name, zone_id, project_id):
    return os.path.join(
        config.Paths().container_config_path,
        ClusterConfig._CONFIG_DIR_FORMAT.format(
            project=project_id, zone=zone_id, cluster=cluster_name
        ),
    )

  @staticmethod
  def KubeContext(cluster_name, zone_id, project_id, override=None):
    if override:
      return override
    return ClusterConfig.KUBECONTEXT_FORMAT.format(
        project=project_id, cluster=cluster_name, zone=zone_id
    )

  def GenKubeconfig(self):
    """Generate kubeconfig for this cluster."""
    context = self.kube_context
    kubeconfig = kconfig.Kubeconfig.Default()
    cluster_kwargs = {}
    user_kwargs = {
        'auth_provider': self.auth_provider,
    }
    if self.has_ca_cert:
      cluster_kwargs['ca_data'] = self.ca_data
    if self.has_cert_data:
      user_kwargs['cert_data'] = self.client_cert_data
      user_kwargs['key_data'] = self.client_key_data
    if self.has_dns_endpoint:
      cluster_kwargs['has_dns_endpoint'] = True
    if self.has_impersonate_service_account:
      user_kwargs['impersonate_service_account'] = (
          self.impersonate_service_account
      )
    if self.use_iam_token:
      user_kwargs['iam_token'] = _GenerateIamToken()

    # Use same key for context, cluster, and user
    kubeconfig.contexts[context] = kconfig.Context(context, context, context)
    kubeconfig.users[context] = kconfig.User(context, **user_kwargs)
    kubeconfig.clusters[context] = kconfig.Cluster(
        context, self.server, **cluster_kwargs
    )
    kubeconfig.SetCurrentContext(context)
    kubeconfig.SaveToFile()

    path = kconfig.Kubeconfig.DefaultPath()
    log.debug('Saved kubeconfig to %s', path)
    log.status.Print(
        KUBECONFIG_USAGE_FMT.format(cluster=self.cluster_name, context=context)
    )

  @classmethod
  def Persist(
      cls,
      cluster,
      project_id,
      use_internal_ip=False,
      cross_connect_subnetwork=None,
      use_private_fqdn=None,
      use_dns_endpoint=None,
      impersonate_service_account=None,
      kubecontext_override=None,
      use_iam_token=False,
  ):
    """Saves config data for the given cluster.

    Persists config file and kubernetes auth file for the given cluster
    to cloud-sdk config directory and returns ClusterConfig object
    encapsulating the same data.

    Args:
      cluster: valid Cluster message to persist config data for.
      project_id: project that owns this cluster.
      use_internal_ip: whether to persist the internal IP of the endpoint.
      cross_connect_subnetwork: full path of the cross connect subnet whose
        endpoint to persist (optional)
      use_private_fqdn: whether to persist the private fqdn.
      use_dns_endpoint: whether to generate dns endpoint address.
      impersonate_service_account: the service account to impersonate when
        connecting to the cluster.
      kubecontext_override: the path to the kubeconfig file to write to.
      use_iam_token: whether to generate and persist an IAM token in the
        kubeconfig file.

    Returns:
      ClusterConfig of the persisted data.

    Raises:
      Error: if cluster has no endpoint (will be the case for first few
        seconds while cluster is PROVISIONING).
    """
    endpoint = _GetClusterEndpoint(
        cluster,
        use_internal_ip,
        cross_connect_subnetwork,
        use_private_fqdn,
        use_dns_endpoint,
    )
    kwargs = {
        'cluster_name': cluster.name,
        'zone_id': cluster.zone,
        'project_id': project_id,
        'server': 'https://' + endpoint,
        'kubecontext_override': kubecontext_override,
        'use_iam_token': use_iam_token,
    }
    if use_dns_endpoint or (
        # TODO(b/365115169)
        cluster.controlPlaneEndpointsConfig is not None
        and cluster.controlPlaneEndpointsConfig.ipEndpointsConfig is not None
        and not cluster.controlPlaneEndpointsConfig.ipEndpointsConfig.enabled
    ):
      kwargs['dns_endpoint'] = endpoint
    auth = cluster.masterAuth
    if auth and auth.clusterCaCertificate:
      kwargs['ca_data'] = auth.clusterCaCertificate
    else:
      # This should not happen unless the cluster is in an unusual error
      # state.
      log.warning('Cluster is missing certificate authority data.')

    if cls.UseGCPAuthProvider():
      kwargs['auth_provider'] = 'gcp'
    else:
      if auth.clientCertificate and auth.clientKey:
        kwargs['client_key_data'] = auth.clientKey
        kwargs['client_cert_data'] = auth.clientCertificate
    if impersonate_service_account:
      kwargs['impersonate_service_account'] = impersonate_service_account

    c_config = cls(**kwargs)
    c_config.GenKubeconfig()
    return c_config

  @classmethod
  def Load(cls, cluster_name, zone_id, project_id, kubecontext_override):
    """Load and verify config for given cluster.

    Args:
      cluster_name: name of cluster to load config for.
      zone_id: compute zone the cluster is running in.
      project_id: project in which the cluster is running.
      kubecontext_override: the path to the kubeconfig file to read from.

    Returns:
      ClusterConfig for the cluster, or None if config data is missing or
      incomplete.
    """
    # TODO(b/323599307): Move this to a test-only package.
    log.debug(
        'Loading cluster config for cluster=%s, zone=%s project=%s',
        cluster_name,
        zone_id,
        project_id,
    )
    k = kconfig.Kubeconfig.Default()
    key = cls.KubeContext(
        cluster_name, zone_id, project_id, kubecontext_override
    )
    cluster = k.clusters.get(key) and k.clusters[key].get('cluster')
    user = k.users.get(key) and k.users[key].get('user')
    context = k.contexts.get(key) and k.contexts[key].get('context')
    if not cluster or not user or not context:
      log.debug('missing kubeconfig entries for %s', key)
      return None
    if context.get('user') != key or context.get('cluster') != key:
      log.debug('invalid context %s', context)
      return None

    # Verify cluster data
    server = cluster.get('server')
    uses_ip_endpoint = re.search(r'\d+\.\d+\.\d+\.\d+', server)
    insecure = cluster.get('insecure-skip-tls-verify')
    ca_data = cluster.get('certificate-authority-data')
    if not server:
      log.debug('missing cluster.server entry for %s', key)
      return None
    if insecure:
      if ca_data:
        log.debug(
            'cluster cannot specify both certificate-authority-data '
            'and insecure-skip-tls-verify'
        )
        return None
    elif not ca_data and uses_ip_endpoint:
      log.debug(
          'cluster must specify one of '
          'certificate-authority-data|insecure-skip-tls-verify'
      )
      return None

    # Verify user data
    auth_provider = user.get('auth-provider')
    exec_auth = user.get('exec')
    cert_data = user.get('client-certificate-data')
    key_data = user.get('client-key-data')
    cert_auth = cert_data and key_data
    has_valid_auth = auth_provider or exec_auth or cert_auth
    if not has_valid_auth:
      log.debug('missing auth info for user %s: %s', key, user)
      return None
    # Construct ClusterConfig
    kwargs = {
        'cluster_name': cluster_name,
        'zone_id': zone_id,
        'project_id': project_id,
        'server': server,
        'auth_provider': auth_provider,
        'exec_auth': exec_auth,
        'ca_data': ca_data,
        'client_key_data': key_data,
        'client_cert_data': cert_data,
    }
    return cls(**kwargs)

  @classmethod
  def Purge(cls, cluster_name, zone_id, project_id, kubecontext_override):
    config_dir = cls.GetConfigDir(cluster_name, zone_id, project_id)
    if os.path.exists(config_dir):
      file_utils.RmTree(config_dir)
    # purge from kubeconfig
    kubeconfig = kconfig.Kubeconfig.Default()
    kubeconfig.Clear(
        cls.KubeContext(cluster_name, zone_id, project_id, kubecontext_override)
    )
    kubeconfig.SaveToFile()
    log.debug('Purged cluster config from %s', config_dir)


def CalculateMaxNodeNumberByPodRange(cluster_ipv4_cidr):
  """Calculate the maximum number of nodes for route based clusters.

  Args:
    cluster_ipv4_cidr: The cluster IPv4 CIDR requested. If cluster_ipv4_cidr is
      not specified, GKE_DEFAULT_POD_RANGE will be used.

  Returns:
    The maximum number of nodes the cluster can have.
    The function returns -1 in case of error.
  """

  if cluster_ipv4_cidr is None:
    pod_range = GKE_DEFAULT_POD_RANGE
  else:
    blocksize = cluster_ipv4_cidr.split('/')[-1]
    if not blocksize.isdecimal():
      return -1
    pod_range = int(blocksize)
    if pod_range < 0:
      return -1
  pod_range_ips = 2 ** (32 - pod_range) - 2 ** (
      32 - GKE_ROUTE_BASED_SERVICE_RANGE
  )
  pod_range_ips_per_node = 2 ** (32 - GKE_DEFAULT_POD_RANGE_PER_NODE)
  if pod_range_ips < pod_range_ips_per_node:
    return -1
  return int(pod_range_ips / pod_range_ips_per_node)


def LoadEvictionMapConfig(parent_name, opts, msg_type, field_spec):
  """Loads eviction map configuration.

  Args:
    parent_name: The parent name of the eviction map configuration.
    opts: The eviction map configuration contents.
    msg_type: The message type of the eviction map configuration.
    field_spec: The field spec of the eviction map configuration.

  Returns:
    The eviction map configuration message.
  """

  map_opts = opts.get(parent_name)
  if map_opts:
    _CheckNodeConfigFields(parent_name, map_opts, field_spec)
    msg_instance = msg_type()
    for key in field_spec:
      if key in map_opts:
        setattr(msg_instance, key, map_opts[key])
    return msg_instance
  return None


def LoadSystemConfigFromYAML(
    node_config, content, opt_readonly_port_flag, messages
):
  """Load system configuration (sysctl & kubelet config) from YAML/JSON file.

  Args:
    node_config: The node config object to be populated.
    content: The YAML/JSON string that contains sysctl and kubelet options.
    opt_readonly_port_flag: kubelet readonly port enabled.
    messages: The message module.

  Raises:
    Error: when there's any errors on parsing the YAML/JSON system config.
  """

  try:
    opts = yaml.load(content)
  except yaml.YAMLParseError as e:
    raise NodeConfigError('config is not valid YAML/JSON: {0}'.format(e))

  _CheckNodeConfigFields(
      '<root>',
      opts,
      {
          NC_KUBELET_CONFIG: dict,
          NC_LINUX_CONFIG: dict,
      },
  )

  # Parse kubelet config options.
  kubelet_config_opts = opts.get(NC_KUBELET_CONFIG)
  if kubelet_config_opts:
    config_fields = {
        NC_CPU_MANAGER_POLICY: str,
        NC_CPU_CFS_QUOTA: bool,
        NC_CPU_CFS_QUOTA_PERIOD: str,
        NC_POD_PIDS_LIMIT: int,
        NC_KUBELET_READONLY_PORT: bool,
        NC_ALLOWED_UNSAFE_SYSCTLS: list,
        NC_CONTAINER_LOG_MAX_SIZE: str,
        NC_CONTAINER_LOG_MAX_FILES: int,
        NC_IMAGE_GC_HIGH_THRESHOLD_PERCENT: int,
        NC_IMAGE_GC_LOW_THRESHOLD_PERCENT: int,
        NC_IMAGE_MINIMUM_GC_AGE: str,
        NC_IMAGE_MAXIMUM_GC_AGE: str,
        NC_TOPOLOGY_MANAGER: dict,
        NC_MEMORY_MANAGER: dict,
        NC_SINGLE_PROCESS_OOMKILL: bool,
        NC_NODE_SWAP_SIZE_GIB: int,
        NC_MAX_PARALLEL_IMAGE_PULLS: int,
        NC_EVICTION_SOFT: dict,
        NC_EVICTION_SOFT_GRACE_PERIOD: dict,
        NC_EVICTION_MINIMUM_RECLAIM: dict,
        NC_EVICTION_MAX_POD_GRACE_PERIOD_SECONDS: int,
    }
    _CheckNodeConfigFields(
        NC_KUBELET_CONFIG, kubelet_config_opts, config_fields
    )
    node_config.kubeletConfig = messages.NodeKubeletConfig()
    node_config.kubeletConfig.cpuManagerPolicy = kubelet_config_opts.get(
        NC_CPU_MANAGER_POLICY
    )
    node_config.kubeletConfig.cpuCfsQuota = kubelet_config_opts.get(
        NC_CPU_CFS_QUOTA
    )
    node_config.kubeletConfig.cpuCfsQuotaPeriod = kubelet_config_opts.get(
        NC_CPU_CFS_QUOTA_PERIOD
    )
    node_config.kubeletConfig.podPidsLimit = kubelet_config_opts.get(
        NC_POD_PIDS_LIMIT
    )
    node_config.kubeletConfig.insecureKubeletReadonlyPortEnabled = (
        kubelet_config_opts.get(NC_KUBELET_READONLY_PORT)
    )
    node_config.kubeletConfig.containerLogMaxSize = kubelet_config_opts.get(
        NC_CONTAINER_LOG_MAX_SIZE
    )
    node_config.kubeletConfig.containerLogMaxFiles = kubelet_config_opts.get(
        NC_CONTAINER_LOG_MAX_FILES
    )
    node_config.kubeletConfig.imageGcLowThresholdPercent = (
        kubelet_config_opts.get(NC_IMAGE_GC_LOW_THRESHOLD_PERCENT)
    )
    node_config.kubeletConfig.imageGcHighThresholdPercent = (
        kubelet_config_opts.get(NC_IMAGE_GC_HIGH_THRESHOLD_PERCENT)
    )
    node_config.kubeletConfig.imageMinimumGcAge = kubelet_config_opts.get(
        NC_IMAGE_MINIMUM_GC_AGE
    )
    node_config.kubeletConfig.imageMaximumGcAge = kubelet_config_opts.get(
        NC_IMAGE_MAXIMUM_GC_AGE
    )
    node_config.kubeletConfig.singleProcessOomKill = kubelet_config_opts.get(
        NC_SINGLE_PROCESS_OOMKILL
    )
    node_config.kubeletConfig.nodeSwapSizeGib = kubelet_config_opts.get(
        NC_NODE_SWAP_SIZE_GIB
    )
    node_config.kubeletConfig.maxParallelImagePulls = kubelet_config_opts.get(
        NC_MAX_PARALLEL_IMAGE_PULLS
    )

    # Populate eviction fields
    eviction_map_string_fields = {
        'memoryAvailable': str,
        'nodefsAvailable': str,
        'nodefsInodesFree': str,
        'imagefsAvailable': str,
        'imagefsInodesFree': str,
        'pidAvailable': str,
    }

    node_config.kubeletConfig.evictionSoft = LoadEvictionMapConfig(
        NC_EVICTION_SOFT,
        kubelet_config_opts,
        messages.EvictionSignals,
        eviction_map_string_fields,
    )
    node_config.kubeletConfig.evictionSoftGracePeriod = LoadEvictionMapConfig(
        NC_EVICTION_SOFT_GRACE_PERIOD,
        kubelet_config_opts,
        messages.EvictionGracePeriod,
        eviction_map_string_fields,
    )
    node_config.kubeletConfig.evictionMinimumReclaim = LoadEvictionMapConfig(
        NC_EVICTION_MINIMUM_RECLAIM,
        kubelet_config_opts,
        messages.EvictionMinimumReclaim,
        eviction_map_string_fields,
    )
    node_config.kubeletConfig.evictionMaxPodGracePeriodSeconds = (
        kubelet_config_opts.get(NC_EVICTION_MAX_POD_GRACE_PERIOD_SECONDS)
    )

    # Parse memory manager.
    memory_manager_opts = kubelet_config_opts.get(NC_MEMORY_MANAGER)
    if memory_manager_opts:
      node_config.kubeletConfig.memoryManager = messages.MemoryManager()
      memory_manager_policy = memory_manager_opts.get(NC_MEMORY_MANAGER_POLICY)
      if memory_manager_policy:
        node_config.kubeletConfig.memoryManager.policy = memory_manager_policy
    # Parse topology manager.
    topology_manager_opts = kubelet_config_opts.get(NC_TOPOLOGY_MANAGER)
    if topology_manager_opts:
      node_config.kubeletConfig.topologyManager = messages.TopologyManager()
      topology_manager_policy = topology_manager_opts.get(
          NC_TOPOLOGY_MANAGER_POLICY
      )
      if topology_manager_policy:
        node_config.kubeletConfig.topologyManager.policy = (
            topology_manager_policy
        )
      topology_manager_scope = topology_manager_opts.get(
          NC_TOPOLOGY_MANAGER_SCOPE
      )
      if topology_manager_scope:
        node_config.kubeletConfig.topologyManager.scope = topology_manager_scope

    sysctls = kubelet_config_opts.get(NC_ALLOWED_UNSAFE_SYSCTLS)
    if sysctls:
      node_config.kubeletConfig.allowedUnsafeSysctls = sysctls

  ro_in_cfg = (
      node_config is not None
      and node_config.kubeletConfig is not None
      and node_config.kubeletConfig.insecureKubeletReadonlyPortEnabled
      is not None
  )
  ro_in_flag = opt_readonly_port_flag is not None
  if ro_in_cfg and ro_in_flag:
    raise NodeConfigError(INVALID_NC_FLAG_CONFIG_OVERLAP)

  # Parse Linux config options.
  linux_config_opts = opts.get(NC_LINUX_CONFIG)
  if linux_config_opts:
    _CheckNodeConfigFields(
        NC_LINUX_CONFIG,
        linux_config_opts,
        {
            NC_SYSCTL: dict,
            NC_CGROUP_MODE: str,
            NC_HUGEPAGE: dict,
            NC_TRANSPARENT_HUGEPAGE_ENABLED: str,
            NC_TRANSPARENT_HUGEPAGE_DEFRAG: str,
            NC_SWAP_CONFIG: dict,
            NC_KERNEL_OVERRIDES: dict,
            NC_ADDITIONAL_ETC_HOSTS: list,
            NC_ADDITIONAL_ETC_SYSTEMD_RESOLVED_CONF: list,
            NC_ADDITIONAL_ETC_RESOLV_CONF: list,
            NC_TIME_ZONE: str,
            NC_CUSTOM_NODE_INIT: dict,
        },
    )
    node_config.linuxNodeConfig = messages.LinuxNodeConfig()
    sysctl_opts = linux_config_opts.get(NC_SYSCTL)
    if sysctl_opts:
      node_config.linuxNodeConfig.sysctls = (
          node_config.linuxNodeConfig.SysctlsValue()
      )
      for key, value in sorted(six.iteritems(sysctl_opts)):
        _CheckNodeConfigValueType(key, value, str)
        node_config.linuxNodeConfig.sysctls.additionalProperties.append(
            node_config.linuxNodeConfig.sysctls.AdditionalProperty(
                key=key, value=value
            )
        )
    cgroup_mode_opts = linux_config_opts.get(NC_CGROUP_MODE)
    if cgroup_mode_opts:
      if not hasattr(messages.LinuxNodeConfig, 'cgroupMode'):
        raise NodeConfigError(
            'setting cgroupMode as {0} is not supported'.format(
                cgroup_mode_opts
            )
        )
      cgroup_mode_mapping = {
          'CGROUP_MODE_UNSPECIFIED': (
              messages.LinuxNodeConfig.CgroupModeValueValuesEnum.CGROUP_MODE_UNSPECIFIED
          ),
          'CGROUP_MODE_V1': (
              messages.LinuxNodeConfig.CgroupModeValueValuesEnum.CGROUP_MODE_V1
          ),
          'CGROUP_MODE_V2': (
              messages.LinuxNodeConfig.CgroupModeValueValuesEnum.CGROUP_MODE_V2
          ),
      }
      if cgroup_mode_opts not in cgroup_mode_mapping:
        raise NodeConfigError(
            'cgroup mode "{0}" is not supported, the supported options are'
            ' CGROUP_MODE_UNSPECIFIED, CGROUP_MODE_V1, CGROUP_MODE_V2'.format(
                cgroup_mode_opts
            )
        )
      # Warning if setting cgroup mode to V1.
      elif cgroup_mode_opts == 'CGROUP_MODE_V1':
        log.warning(CGROUPV1_DEPRECATED_MSG)

      node_config.linuxNodeConfig.cgroupMode = cgroup_mode_mapping[
          cgroup_mode_opts
      ]

    transparent_hugepage_enabled_opts = linux_config_opts.get(
        NC_TRANSPARENT_HUGEPAGE_ENABLED
    )
    if transparent_hugepage_enabled_opts:
      transparent_hugepage_enabled_mapping = {
          'TRANSPARENT_HUGEPAGE_ENABLED_UNSPECIFIED': (
              messages.LinuxNodeConfig.TransparentHugepageEnabledValueValuesEnum.TRANSPARENT_HUGEPAGE_ENABLED_UNSPECIFIED
          ),
          'TRANSPARENT_HUGEPAGE_ENABLED_ALWAYS': (
              messages.LinuxNodeConfig.TransparentHugepageEnabledValueValuesEnum.TRANSPARENT_HUGEPAGE_ENABLED_ALWAYS
          ),
          'TRANSPARENT_HUGEPAGE_ENABLED_MADVISE': (
              messages.LinuxNodeConfig.TransparentHugepageEnabledValueValuesEnum.TRANSPARENT_HUGEPAGE_ENABLED_MADVISE
          ),
          'TRANSPARENT_HUGEPAGE_ENABLED_NEVER': (
              messages.LinuxNodeConfig.TransparentHugepageEnabledValueValuesEnum.TRANSPARENT_HUGEPAGE_ENABLED_NEVER
          ),
      }
      if (
          transparent_hugepage_enabled_opts
          not in transparent_hugepage_enabled_mapping
      ):
        raise NodeConfigError(
            'transparent hugepage enabled "{0}" is not supported, the supported'
            ' options are TRANSPARENT_HUGEPAGE_ENABLED_ALWAYS,'
            ' TRANSPARENT_HUGEPAGE_ENABLED_MADVISE,'
            ' TRANSPARENT_HUGEPAGE_ENABLED_NEVER,'
            ' TRANSPARENT_HUGEPAGE_ENABLED_UNSPECIFIED'.format(
                transparent_hugepage_enabled_opts
            )
        )
      node_config.linuxNodeConfig.transparentHugepageEnabled = (
          transparent_hugepage_enabled_mapping[
              transparent_hugepage_enabled_opts
          ]
      )
    transparent_hugepage_defrag_opts = linux_config_opts.get(
        NC_TRANSPARENT_HUGEPAGE_DEFRAG
    )
    if transparent_hugepage_defrag_opts:
      transparent_hugepage_defrag_mapping = {
          'TRANSPARENT_HUGEPAGE_DEFRAG_UNSPECIFIED': (
              messages.LinuxNodeConfig.TransparentHugepageDefragValueValuesEnum.TRANSPARENT_HUGEPAGE_DEFRAG_UNSPECIFIED
          ),
          'TRANSPARENT_HUGEPAGE_DEFRAG_ALWAYS': (
              messages.LinuxNodeConfig.TransparentHugepageDefragValueValuesEnum.TRANSPARENT_HUGEPAGE_DEFRAG_ALWAYS
          ),
          'TRANSPARENT_HUGEPAGE_DEFRAG_DEFER': (
              messages.LinuxNodeConfig.TransparentHugepageDefragValueValuesEnum.TRANSPARENT_HUGEPAGE_DEFRAG_DEFER
          ),
          'TRANSPARENT_HUGEPAGE_DEFRAG_DEFER_WITH_MADVISE': (
              messages.LinuxNodeConfig.TransparentHugepageDefragValueValuesEnum.TRANSPARENT_HUGEPAGE_DEFRAG_DEFER_WITH_MADVISE
          ),
          'TRANSPARENT_HUGEPAGE_DEFRAG_MADVISE': (
              messages.LinuxNodeConfig.TransparentHugepageDefragValueValuesEnum.TRANSPARENT_HUGEPAGE_DEFRAG_MADVISE
          ),
          'TRANSPARENT_HUGEPAGE_DEFRAG_NEVER': (
              messages.LinuxNodeConfig.TransparentHugepageDefragValueValuesEnum.TRANSPARENT_HUGEPAGE_DEFRAG_NEVER
          ),
      }
      if (
          transparent_hugepage_defrag_opts
          not in transparent_hugepage_defrag_mapping
      ):
        raise NodeConfigError(
            'transparent hugepage defrag "{0}" is not supported, the supported'
            ' options are TRANSPARENT_HUGEPAGE_DEFRAG_ALWAYS,'
            ' TRANSPARENT_HUGEPAGE_DEFRAG_DEFER,'
            ' TRANSPARENT_HUGEPAGE_DEFRAG_DEFER_WITH_MADVISE,'
            ' TRANSPARENT_HUGEPAGE_DEFRAG_MADVISE,'
            ' TRANSPARENT_HUGEPAGE_DEFRAG_NEVER,'
            ' TRANSPARENT_HUGEPAGE_DEFRAG_UNSPECIFIED'.format(
                transparent_hugepage_defrag_opts
            )
        )
      node_config.linuxNodeConfig.transparentHugepageDefrag = (
          transparent_hugepage_defrag_mapping[transparent_hugepage_defrag_opts]
      )
    # Parse hugepages.
    hugepage_opts = linux_config_opts.get(NC_HUGEPAGE)
    if hugepage_opts:
      node_config.linuxNodeConfig.hugepages = messages.HugepagesConfig()
      hugepage_size2m = hugepage_opts.get(NC_HUGEPAGE_2M)
      if hugepage_size2m:
        node_config.linuxNodeConfig.hugepages.hugepageSize2m = hugepage_size2m
      hugepage_size1g = hugepage_opts.get(NC_HUGEPAGE_1G)
      if hugepage_size1g:
        node_config.linuxNodeConfig.hugepages.hugepageSize1g = hugepage_size1g
    # Parse swap config.
    if swap_config_opts := linux_config_opts.get(NC_SWAP_CONFIG):
      node_config.linuxNodeConfig.swapConfig = messages.SwapConfig()
      _CheckNodeConfigFields(
          NC_SWAP_CONFIG,
          swap_config_opts,
          {
              NC_SWAP_CONFIG_ENABLED: bool,
              NC_SWAP_CONFIG_ENCRYPTION_CONFIG: dict,
              NC_SWAP_CONFIG_BOOT_DISK_PROFILE: dict,
              NC_SWAP_CONFIG_EPHEMERAL_LOCAL_SSD_PROFILE: dict,
              NC_SWAP_CONFIG_DEDICATED_LOCAL_SSD_PROFILE: dict,
          },
      )
      enabled = swap_config_opts.get(NC_SWAP_CONFIG_ENABLED)
      if enabled is not None:
        node_config.linuxNodeConfig.swapConfig.enabled = enabled
      encryption_config_opts = swap_config_opts.get(
          NC_SWAP_CONFIG_ENCRYPTION_CONFIG
      )
      if encryption_config_opts:
        node_config.linuxNodeConfig.swapConfig.encryptionConfig = (
            messages.EncryptionConfig()
        )
        _CheckNodeConfigFields(
            NC_SWAP_CONFIG_ENCRYPTION_CONFIG,
            encryption_config_opts,
            {NC_SWAP_CONFIG_ENCRYPTION_CONFIG_DISABLED: bool},
        )
        disabled = encryption_config_opts.get(
            NC_SWAP_CONFIG_ENCRYPTION_CONFIG_DISABLED
        )
        if disabled is not None:
          node_config.linuxNodeConfig.swapConfig.encryptionConfig.disabled = (
              disabled
          )
      boot_disk_profile_opts = swap_config_opts.get(
          NC_SWAP_CONFIG_BOOT_DISK_PROFILE
      )
      if boot_disk_profile_opts:
        boot_disk_profile_msg = messages.BootDiskProfile()
        _CheckNodeConfigFields(
            NC_SWAP_CONFIG_BOOT_DISK_PROFILE,
            boot_disk_profile_opts,
            {
                NC_SWAP_CONFIG_SWAP_SIZE_GIB: int,
                NC_SWAP_CONFIG_SWAP_SIZE_PERCENT: int,
            },
        )
        swap_size_gib = boot_disk_profile_opts.get(NC_SWAP_CONFIG_SWAP_SIZE_GIB)
        if swap_size_gib is not None:
          boot_disk_profile_msg.swapSizeGib = swap_size_gib
        swap_size_percent = boot_disk_profile_opts.get(
            NC_SWAP_CONFIG_SWAP_SIZE_PERCENT
        )
        if swap_size_percent is not None:
          boot_disk_profile_msg.swapSizePercent = swap_size_percent
        node_config.linuxNodeConfig.swapConfig.bootDiskProfile = (
            boot_disk_profile_msg
        )
      ephemeral_local_ssd_profile_opts = swap_config_opts.get(
          NC_SWAP_CONFIG_EPHEMERAL_LOCAL_SSD_PROFILE
      )
      if ephemeral_local_ssd_profile_opts:
        ephemeral_local_ssd_profile_msg = (
            messages.EphemeralLocalSsdProfile()
        )
        _CheckNodeConfigFields(
            NC_SWAP_CONFIG_EPHEMERAL_LOCAL_SSD_PROFILE,
            ephemeral_local_ssd_profile_opts,
            {
                NC_SWAP_CONFIG_SWAP_SIZE_GIB: int,
                NC_SWAP_CONFIG_SWAP_SIZE_PERCENT: int,
            },
        )
        swap_size_gib = ephemeral_local_ssd_profile_opts.get(
            NC_SWAP_CONFIG_SWAP_SIZE_GIB
        )
        if swap_size_gib is not None:
          ephemeral_local_ssd_profile_msg.swapSizeGib = swap_size_gib
        swap_size_percent = ephemeral_local_ssd_profile_opts.get(
            NC_SWAP_CONFIG_SWAP_SIZE_PERCENT
        )
        if swap_size_percent is not None:
          ephemeral_local_ssd_profile_msg.swapSizePercent = swap_size_percent
        node_config.linuxNodeConfig.swapConfig.ephemeralLocalSsdProfile = (
            ephemeral_local_ssd_profile_msg
        )
      dedicated_local_ssd_profile_opts = swap_config_opts.get(
          NC_SWAP_CONFIG_DEDICATED_LOCAL_SSD_PROFILE
      )
      if dedicated_local_ssd_profile_opts:
        dedicated_local_ssd_profile_msg = (
            messages.DedicatedLocalSsdProfile()
        )
        _CheckNodeConfigFields(
            NC_SWAP_CONFIG_DEDICATED_LOCAL_SSD_PROFILE,
            dedicated_local_ssd_profile_opts,
            {NC_SWAP_CONFIG_DISK_COUNT: int},
        )
        disk_count = dedicated_local_ssd_profile_opts.get(
            NC_SWAP_CONFIG_DISK_COUNT
        )
        if disk_count is not None:
          dedicated_local_ssd_profile_msg.diskCount = disk_count
        node_config.linuxNodeConfig.swapConfig.dedicatedLocalSsdProfile = (
            dedicated_local_ssd_profile_msg
        )

    # Parse kernel overrides.
    kernel_overrides_opts = linux_config_opts.get(NC_KERNEL_OVERRIDES)
    if kernel_overrides_opts is not None:
      node_config.linuxNodeConfig.kernelOverrides = messages.KernelOverrides()
      _CheckNodeConfigFields(
          NC_KERNEL_OVERRIDES,
          kernel_overrides_opts,
          {
              NC_KERNEL_COMMANDLINE_OVERRIDES: dict,
              NC_LRU_GEN: dict,
          },
      )
      kernel_commandline = kernel_overrides_opts.get(
          NC_KERNEL_COMMANDLINE_OVERRIDES
      )
      if kernel_commandline is not None:
        spec_rstack_overflow = kernel_commandline.get(
            NC_KERNEL_SPEC_RSTACK_OVERFLOW
        )
        init_on_alloc = kernel_commandline.get(NC_KERNEL_INIT_ON_ALLOC)
        node_config.linuxNodeConfig.kernelOverrides.kernelCommandlineOverrides = (
            messages.KernelCommandlineOverrides()
        )
        if spec_rstack_overflow is not None:
          spec_rstack_overflow_off = 'SPEC_RSTACK_OVERFLOW_OFF'
          if spec_rstack_overflow == spec_rstack_overflow_off:
            node_config.linuxNodeConfig.kernelOverrides.kernelCommandlineOverrides.specRstackOverflow = (
                messages.KernelCommandlineOverrides.SpecRstackOverflowValueValuesEnum.SPEC_RSTACK_OVERFLOW_OFF
            )
          else:
            raise NodeConfigError(
                'setting specRstackOverflow as {0} is not supported. The'
                ' supported options is {1}'.format(
                    spec_rstack_overflow, spec_rstack_overflow_off
                )
            )
        if init_on_alloc is not None:
          init_on_alloc_off = 'INIT_ON_ALLOC_OFF'
          if init_on_alloc == init_on_alloc_off:
            node_config.linuxNodeConfig.kernelOverrides.kernelCommandlineOverrides.initOnAlloc = (
                messages.KernelCommandlineOverrides.InitOnAllocValueValuesEnum.INIT_ON_ALLOC_OFF
            )
          else:
            raise NodeConfigError(
                'setting initOnAlloc as {0} is not supported. The supported'
                ' options is {1}'.format(init_on_alloc, init_on_alloc_off)
            )
      lru_gen = kernel_overrides_opts.get(NC_LRU_GEN)
      if lru_gen is not None:
        node_config.linuxNodeConfig.kernelOverrides.lruGen = messages.LRUGen()
        lru_gen_enabled = lru_gen.get(NC_LRU_GEN_ENABLED)
        min_ttl_ms = lru_gen.get(NC_LRU_GEN_MIN_TTL_MS)
        if lru_gen_enabled is not None:
          node_config.linuxNodeConfig.kernelOverrides.lruGen.enabled = (
              lru_gen_enabled
          )
        if min_ttl_ms is not None:
          node_config.linuxNodeConfig.kernelOverrides.lruGen.minTtlMs = (
              min_ttl_ms
          )

    # Parse additional etc hosts.
    additional_etc_hosts_opts = linux_config_opts.get(NC_ADDITIONAL_ETC_HOSTS)
    node_config.linuxNodeConfig.additionalEtcHosts = []
    if additional_etc_hosts_opts:
      for i, opts in enumerate(additional_etc_hosts_opts):
        _CheckNodeConfigFields(
            '{0}[{1}]'.format(NC_ADDITIONAL_ETC_HOSTS, i),
            opts,
            {
                NC_ETC_HOSTS_ENTRY_IP: str,
                NC_ETC_HOSTS_ENTRY_HOST: str,
            },
        )
        etc_hosts_entry = messages.EtcHostsEntry()
        etc_hosts_entry.ip = opts.get(NC_ETC_HOSTS_ENTRY_IP)
        etc_hosts_entry.host = opts.get(NC_ETC_HOSTS_ENTRY_HOST)
        node_config.linuxNodeConfig.additionalEtcHosts.append(etc_hosts_entry)

    # Parse additional etc systemd resolved conf.
    additional_etc_systemd_resolved_conf_opts = linux_config_opts.get(
        NC_ADDITIONAL_ETC_SYSTEMD_RESOLVED_CONF
    )
    node_config.linuxNodeConfig.additionalEtcSystemdResolvedConf = []
    if additional_etc_systemd_resolved_conf_opts:
      for i, opts in enumerate(additional_etc_systemd_resolved_conf_opts):
        _CheckNodeConfigFields(
            '{0}[{1}]'.format(NC_ADDITIONAL_ETC_SYSTEMD_RESOLVED_CONF, i),
            opts,
            {
                NC_RESOLVED_CONF_ENTRY_KEY: str,
                NC_RESOLVED_CONF_ENTRY_VALUE: list,
            },
        )
        resolved_conf_entry = messages.ResolvedConfEntry()
        resolved_conf_entry.key = opts.get(NC_RESOLVED_CONF_ENTRY_KEY)
        resolved_conf_entry.value = opts.get(NC_RESOLVED_CONF_ENTRY_VALUE)
        node_config.linuxNodeConfig.additionalEtcSystemdResolvedConf.append(
            resolved_conf_entry
        )

    # Parse additional etc resolv conf.
    additional_etc_resolv_conf_opts = linux_config_opts.get(
        NC_ADDITIONAL_ETC_RESOLV_CONF
    )
    node_config.linuxNodeConfig.additionalEtcResolvConf = []
    if additional_etc_resolv_conf_opts:
      for i, opts in enumerate(additional_etc_resolv_conf_opts):
        _CheckNodeConfigFields(
            '{0}[{1}]'.format(NC_ADDITIONAL_ETC_RESOLV_CONF, i),
            opts,
            {
                NC_RESOLVED_CONF_ENTRY_KEY: str,
                NC_RESOLVED_CONF_ENTRY_VALUE: list,
            },
        )
        resolved_conf_entry = messages.ResolvedConfEntry()
        resolved_conf_entry.key = opts.get(NC_RESOLVED_CONF_ENTRY_KEY)
        resolved_conf_entry.value = opts.get(NC_RESOLVED_CONF_ENTRY_VALUE)
        node_config.linuxNodeConfig.additionalEtcResolvConf.append(
            resolved_conf_entry
        )

    # Parse time zone.
    time_zone_opts = linux_config_opts.get(NC_TIME_ZONE)
    if time_zone_opts:
      node_config.linuxNodeConfig.timeZone = time_zone_opts

    # Parse custom node init.
    custom_node_init_opts = linux_config_opts.get(NC_CUSTOM_NODE_INIT)
    if custom_node_init_opts:
      node_config.linuxNodeConfig.customNodeInit = messages.CustomNodeInit()
      _CheckNodeConfigFields(
          NC_CUSTOM_NODE_INIT,
          custom_node_init_opts,
          {NC_CUSTOM_NODE_INIT_SCRIPT: dict},
      )
      init_script_opts = custom_node_init_opts.get(NC_CUSTOM_NODE_INIT_SCRIPT)
      node_config.linuxNodeConfig.customNodeInit.initScript = (
          messages.InitScript()
      )
      if init_script_opts:
        _CheckNodeConfigFields(
            NC_CUSTOM_NODE_INIT_SCRIPT,
            init_script_opts,
            {
                NC_CUSTOM_NODE_INIT_SCRIPT_GCS_URI: str,
                NC_CUSTOM_NODE_INIT_SCRIPT_GCS_GENERATION: int,
                NC_CUSTOM_NODE_INIT_SCRIPT_ARGS: list,
            },
        )
        node_config.linuxNodeConfig.customNodeInit.initScript.gcsUri = (
            init_script_opts.get(NC_CUSTOM_NODE_INIT_SCRIPT_GCS_URI)
        )
        node_config.linuxNodeConfig.customNodeInit.initScript.gcsGeneration = (
            init_script_opts.get(NC_CUSTOM_NODE_INIT_SCRIPT_GCS_GENERATION)
        )
        init_args = init_script_opts.get(NC_CUSTOM_NODE_INIT_SCRIPT_ARGS)
        if init_args is not None:
          node_config.linuxNodeConfig.customNodeInit.initScript.args = init_args


def CheckForCgroupModeV1(pool):
  """Check cgroup mode of the node pool and print a warning if it is V1."""
  if hasattr(pool, 'config') and hasattr(pool.config, 'effectiveCgroupMode'):
    if (
        pool.config.effectiveCgroupMode
        and pool.config.effectiveCgroupMode.name == 'EFFECTIVE_CGROUP_MODE_V1'
    ):
      log.warning(CGROUPV1_NODEPOOLS_MSG.format(pool.name))


def LoadContainerdConfigFromYAML(containerd_config, content, messages):
  """Load containerd configuration from YAML/JSON file.

  Args:
    containerd_config: The containerd config object to be populated (either from
      a node or from node config defaults).
    content: The YAML/JSON string that contains private CR config.
    messages: The message module.

  Raises:
    Error: when there's any errors on parsing the YAML/JSON system config.
  """
  try:
    opts = yaml.load(content)
  except yaml.YAMLParseError as e:
    raise NodeConfigError('config is not valid YAML/JSON: {0}'.format(e))

  _CheckNodeConfigFields(
      '<root>',
      opts,
      {
          NC_CC_PRIVATE_CR_CONFIG: dict,
          NC_CC_WRITABLE_CGROUPS: dict,
          NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS: list,
      },
  )

  # Parse private container registry options.
  if private_registry_opts := opts.get(NC_CC_PRIVATE_CR_CONFIG):
    config_fields = {
        NC_CC_PRIVATE_CR_CONFIG_ENABLED: bool,
        NC_CC_CA_CONFIG: list,
    }
    _CheckNodeConfigFields(
        NC_CC_PRIVATE_CR_CONFIG, private_registry_opts, config_fields
    )
    containerd_config.privateRegistryAccessConfig = (
        messages.PrivateRegistryAccessConfig()
    )
    containerd_config.privateRegistryAccessConfig.enabled = (
        private_registry_opts.get(NC_CC_PRIVATE_CR_CONFIG_ENABLED)
    )
    if ca_domain_opts := private_registry_opts.get(NC_CC_CA_CONFIG):
      config_fields = {
          NC_CC_GCP_SECRET_CONFIG: dict,
          NC_CC_PRIVATE_CR_FQDNS_CONFIG: list,
      }
      containerd_config.privateRegistryAccessConfig.certificateAuthorityDomainConfig = (
          []
      )
      for i, ca_item in enumerate(ca_domain_opts):
        _CheckNodeConfigFields(
            '{0}[{1}]'.format(NC_CC_CA_CONFIG, i), ca_item, config_fields
        )
        gcp_secret_opts = ca_item.get(NC_CC_GCP_SECRET_CONFIG)
        if not gcp_secret_opts:
          raise NodeConfigError(
              'privateRegistryAccessConfig.certificateAuthorityDomainConfig'
              ' must specify a secret config, none was provided'
          )
        _CheckNodeConfigFields(
            NC_CC_GCP_SECRET_CONFIG,
            gcp_secret_opts,
            {NC_CC_GCP_SECRET_CONFIG_SECRET_URI: str},
        )
        ca_config = messages.CertificateAuthorityDomainConfig()
        ca_config.gcpSecretManagerCertificateConfig = (
            messages.GCPSecretManagerCertificateConfig()
        )
        ca_config.gcpSecretManagerCertificateConfig.secretUri = (
            gcp_secret_opts.get(NC_CC_GCP_SECRET_CONFIG_SECRET_URI)
        )
        ca_config.fqdns = ca_item.get(NC_CC_PRIVATE_CR_FQDNS_CONFIG)
        containerd_config.privateRegistryAccessConfig.certificateAuthorityDomainConfig.append(
            ca_config,
        )

  # Parse writable cgroups options.
  if writable_cgroups_opts := opts.get(NC_CC_WRITABLE_CGROUPS):
    config_fields = {
        NC_CC_WRITABLE_CGROUPS_ENABLED: bool,
    }
    _CheckNodeConfigFields(
        NC_CC_WRITABLE_CGROUPS, writable_cgroups_opts, config_fields
    )
    containerd_config.writableCgroups = messages.WritableCgroups()
    containerd_config.writableCgroups.enabled = writable_cgroups_opts.get(
        NC_CC_WRITABLE_CGROUPS_ENABLED
    )

  registry_hosts_opts = opts.get(NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS)
  if registry_hosts_opts:
    containerd_config.registryHosts = []
    for i, registry_host_opt in enumerate(registry_hosts_opts):
      _CheckNodeConfigFields(
          '{0}[{1}]'.format(NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS, i),
          registry_host_opt,
          {
              NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_SERVER: str,
              NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_HOSTS: list,
          },
      )
      registry_host_msg = messages.RegistryHostConfig()
      registry_host_msg.server = registry_host_opt.get(
          NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_SERVER
      )

      hosts_opts = registry_host_opt.get(
          NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_HOSTS
      )
      if hosts_opts:
        registry_host_msg.hosts = []
        for j, host_opt in enumerate(hosts_opts):
          _CheckNodeConfigFields(
              '{0}[{1}].{2}[{3}]'.format(
                  NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS,
                  i,
                  NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_HOSTS,
                  j,
              ),
              host_opt,
              {
                  NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_HOST: str,
                  NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_OVERRIDE_PATH: bool,
                  NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_CAPABILITIES: list,
                  NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_HEADER: list,
                  NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_DIAL_TIMEOUT: str,
                  NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_CA: list,
                  NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_CLIENT: list,
              },
          )
          host_msg = messages.HostConfig()
          host_msg.host = host_opt.get(
              NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_HOST
          )
          host_msg.overridePath = host_opt.get(
              NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_OVERRIDE_PATH
          )

          capabilities_opts = host_opt.get(
              NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_CAPABILITIES
          )
          if capabilities_opts:
            capability_mapping = {
                'HOST_CAPABILITY_UNSPECIFIED': (
                    messages.HostConfig.CapabilitiesValueListEntryValuesEnum.HOST_CAPABILITY_UNSPECIFIED
                ),
                'HOST_CAPABILITY_PULL': (
                    messages.HostConfig.CapabilitiesValueListEntryValuesEnum.HOST_CAPABILITY_PULL
                ),
                'HOST_CAPABILITY_RESOLVE': (
                    messages.HostConfig.CapabilitiesValueListEntryValuesEnum.HOST_CAPABILITY_RESOLVE
                ),
                'HOST_CAPABILITY_PUSH': (
                    messages.HostConfig.CapabilitiesValueListEntryValuesEnum.HOST_CAPABILITY_PUSH
                ),
            }
            for cap_opt in capabilities_opts:
              if cap_opt not in capability_mapping:
                raise NodeConfigError(
                    'capability "{0}" is not supported, the supported options'
                    ' are HOST_CAPABILITY_PULL, HOST_CAPABILITY_RESOLVE,'
                    ' HOST_CAPABILITY_PUSH'.format(cap_opt)
                )
              if not host_msg.capabilities:
                host_msg.capabilities = []
              host_msg.capabilities.append(capability_mapping[cap_opt])

          header_opts = host_opt.get(
              NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_HEADER
          )
          if header_opts:
            host_msg.header = []
            for header_opt in header_opts:
              _CheckNodeConfigFields(
                  'header',
                  header_opt,
                  {
                      NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_HEADER_KEY: str,
                      NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_HEADER_VALUE: list,
                  },
              )
              header_msg = messages.RegistryHeader()
              header_msg.key = header_opt.get(
                  NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_HEADER_KEY
              )
              header_msg.value = header_opt.get(
                  NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_HEADER_VALUE
              )
              host_msg.header.append(header_msg)

          dial_timeout_opt = host_opt.get(
              NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_DIAL_TIMEOUT
          )
          if dial_timeout_opt:
            host_msg.dialTimeout = dial_timeout_opt

          ca_opts = host_opt.get(NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_CA)
          if ca_opts:
            host_msg.ca = []
            for ca_opt in ca_opts:
              _CheckNodeConfigFields(
                  'ca',
                  ca_opt,
                  {NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_GCP_SECRET_URI: str},
              )
              ca_msg = messages.CertificateConfig()
              ca_msg.gcpSecretManagerSecretUri = ca_opt.get(
                  NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_GCP_SECRET_URI
              )
              host_msg.ca.append(ca_msg)

          client_opts = host_opt.get(
              NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_CLIENT
          )
          if client_opts:
            host_msg.client = []
            for client_opt in client_opts:
              _CheckNodeConfigFields(
                  'client',
                  client_opt,
                  {
                      NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_CLIENT_CERT: dict,
                      NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_CLIENT_KEY: dict,
                  },
              )
              client_msg = messages.CertificateConfigPair()

              cert_opt = client_opt.get(
                  NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_CLIENT_CERT
              )
              if cert_opt:
                _CheckNodeConfigFields(
                    'cert',
                    cert_opt,
                    {
                        NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_GCP_SECRET_URI: (
                            str
                        )
                    },
                )
                cert_msg = messages.CertificateConfig()
                cert_msg.gcpSecretManagerSecretUri = cert_opt.get(
                    NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_GCP_SECRET_URI
                )
                client_msg.cert = cert_msg

              key_opt = client_opt.get(
                  NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_CLIENT_KEY
              )
              if key_opt:
                _CheckNodeConfigFields(
                    'key',
                    key_opt,
                    {
                        NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_GCP_SECRET_URI: (
                            str
                        )
                    },
                )
                key_msg = messages.CertificateConfig()
                key_msg.gcpSecretManagerSecretUri = key_opt.get(
                    NC_CC_PRIVATE_CR_CONFIG_REGISTRY_HOSTS_GCP_SECRET_URI
                )
                client_msg.key = key_msg

              host_msg.client.append(client_msg)

          registry_host_msg.hosts.append(host_msg)
      containerd_config.registryHosts.append(registry_host_msg)


def _CheckNodeConfigFields(parent_name, parent, spec):
  """Check whether the children of the config option are valid or not.

  Args:
    parent_name: The name of the config option to be checked.
    parent: The config option to be checked.
    spec: The spec defining the expected children and their value type.

  Raises:
    NodeConfigError: if there is any unknown fields or any of the fields doesn't
    satisfy the spec.
  """

  _CheckNodeConfigValueType(parent_name, parent, dict)

  unknown_fields = set(parent.keys()) - set(spec.keys())
  if unknown_fields:
    raise NodeConfigError(
        'unknown fields: {0} in "{1}"'.format(
            sorted(list(unknown_fields)), parent_name
        )
    )

  for field_name in parent:
    _CheckNodeConfigValueType(field_name, parent[field_name], spec[field_name])


def _CheckNodeConfigValueType(name, value, value_type):
  """Check whether the config option has the expected value type.

  Args:
    name: The name of the config option to be checked.
    value: The value of the config option to be checked.
    value_type: The expected value type (e.g., str, bool, dict).

  Raises:
    NodeConfigError: if value is not of value_type.
  """

  if not isinstance(value, value_type):
    raise NodeConfigError(
        'value of "{0}" must be {1}'.format(name, value_type.__name__)
    )


def _GetPrivateIPv6CustomMappings():
  return {
      'PRIVATE_IPV6_GOOGLE_ACCESS_DISABLED': 'disabled',
      'PRIVATE_IPV6_GOOGLE_ACCESS_TO_GOOGLE': 'outbound-only',
      'PRIVATE_IPV6_GOOGLE_ACCESS_BIDIRECTIONAL': 'bidirectional',
  }


def GetPrivateIpv6GoogleAccessTypeMapper(messages, hidden=False):
  """Returns a mapper from text options to the PrivateIpv6GoogleAccess enum.

  Args:
    messages: The message module.
    hidden: Whether the flag should be hidden in the choice_arg
  """

  help_text = """
Sets the type of private access to Google services over IPv6.

PRIVATE_IPV6_GOOGLE_ACCESS_TYPE must be one of:

  bidirectional
    Allows Google services to initiate connections to GKE pods in this
    cluster. This is not intended for common use, and requires previous
    integration with Google services.

  disabled
    Default value. Disables private access to Google services over IPv6.

  outbound-only
    Allows GKE pods to make fast, secure requests to Google services
    over IPv6. This is the most common use of private IPv6 access.

  $ gcloud alpha container clusters create \
      --private-ipv6-google-access-type=disabled
  $ gcloud alpha container clusters create \
      --private-ipv6-google-access-type=outbound-only
  $ gcloud alpha container clusters create \
      --private-ipv6-google-access-type=bidirectional
"""
  return arg_utils.ChoiceEnumMapper(
      '--private-ipv6-google-access-type',
      messages.NetworkConfig.PrivateIpv6GoogleAccessValueValuesEnum,
      _GetPrivateIPv6CustomMappings(),
      hidden=hidden,
      help_str=help_text,
  )


def GetPrivateIpv6GoogleAccessTypeMapperForUpdate(messages, hidden=False):
  """Returns a mapper from the text options to the PrivateIpv6GoogleAccess enum.

  Args:
    messages: The message module.
    hidden: Whether the flag should be hidden in the choice_arg. The choice_arg
      will never actually be used for this mode.
  """
  return arg_utils.ChoiceEnumMapper(
      '--private-ipv6-google-access-type',
      messages.ClusterUpdate.DesiredPrivateIpv6GoogleAccessValueValuesEnum,
      _GetPrivateIPv6CustomMappings(),
      hidden=hidden,
      help_str='',
  )


def _GetStackTypeCustomMappings():
  return {
      'IPV4': 'ipv4',
      'IPV4_IPV6': 'ipv4-ipv6',
  }


def GetCreateInTransitEncryptionConfigMapper(messages, hidden=False):
  """Returns a mapper from text options to the InTransitEncryptionConfig enum.

  Args:
    messages: The message module.
    hidden: Whether the flag should be hidden in the choice_arg.
  """

  help_text = """
Sets the in-transit encryption type for dataplane v2 clusters.

--in-transit-encryption must be one of:

  inter-node-transparent
    Changes clusters to use transparent, dataplane v2, node-to-node encryption.

  none:
    Disables dataplane v2 in-transit encryption.

  $ gcloud container clusters create \
      --in-transit-encryption=inter-node-transparent
  $ gcloud container clusters create \
      --in-transit-encryption=none
"""
  return arg_utils.ChoiceEnumMapper(
      '--in-transit-encryption',
      messages.NetworkConfig.InTransitEncryptionConfigValueValuesEnum,
      _GetInTransitEncryptionConfigCustomMappings(),
      hidden=hidden,
      help_str=help_text,
  )


def GetUpdateInTransitEncryptionConfigMapper(messages, hidden=False):
  """Returns a mapper from text options to the InTransitEncryptionConfig enum.

  Args:
    messages: The message module.
    hidden: Whether the flag should be a hidden flag.
  """

  help_text = """
Updates the in-transit encryption type for dataplane v2 clusters.

--in-transit-encryption must be one of:

  inter-node-transparent
    Changes clusters to use transparent, dataplane v2, node-to-node encryption.

  none:
    Disables dataplane v2 in-transit encryption.

  $ gcloud container clusters update \
      --in-transit-encryption=inter-node-transparent
  $ gcloud container clusters update \
      --in-transit-encryption=none
"""
  return arg_utils.ChoiceEnumMapper(
      '--in-transit-encryption',
      messages.ClusterUpdate.DesiredInTransitEncryptionConfigValueValuesEnum,
      _GetInTransitEncryptionConfigCustomMappings(),
      hidden=hidden,
      help_str=help_text,
  )


def _GetInTransitEncryptionConfigCustomMappings():
  return {
      'IN_TRANSIT_ENCRYPTION_INTER_NODE_TRANSPARENT': 'inter-node-transparent',
      'IN_TRANSIT_ENCRYPTION_DISABLED': 'none',
  }


def GetCreateStackTypeMapper(messages, hidden=False):
  """Returns a mapper from text options to the StackType enum.

  Args:
    messages: The message module.
    hidden: Whether the flag should be hidden in the choice_arg
  """

  help_text = """
Sets the stack type for the cluster nodes and pods.

STACK_TYPE must be one of:

  ipv4
    Default value. Creates IPv4 single stack clusters.

  ipv4-ipv6
    Creates dual stack clusters.

  $ gcloud container clusters create \
      --stack-type=ipv4
  $ gcloud container clusters create \
      --stack-type=ipv4-ipv6
"""
  return arg_utils.ChoiceEnumMapper(
      '--stack-type',
      messages.IPAllocationPolicy.StackTypeValueValuesEnum,
      _GetStackTypeCustomMappings(),
      hidden=hidden,
      help_str=help_text,
  )


def GetUpdateStackTypeMapper(messages, hidden=False):
  """Returns a mapper from text options to the StackType enum.

  Args:
    messages: The message module.
    hidden: Whether the flag should be hidden in the choice_arg
  """

  help_text = """
Updates the stack type for the cluster nodes and pods.

STACK_TYPE must be one of:

  ipv4
    Changes clusters to IPv4 single stack clusters.

  ipv4-ipv6
    Changes clusters to dual stack clusters.

  $ gcloud container clusters update \
      --stack-type=ipv4
  $ gcloud container clusters update \
      --stack-type=ipv4-ipv6
"""
  return arg_utils.ChoiceEnumMapper(
      '--stack-type',
      messages.ClusterUpdate.DesiredStackTypeValueValuesEnum,
      _GetStackTypeCustomMappings(),
      hidden=hidden,
      help_str=help_text,
  )


def _GetIpv6AccessTypeCustomMappings():
  return {
      'INTERNAL': 'internal',
      'EXTERNAL': 'external',
  }


def GetIpv6AccessTypeMapper(messages, hidden=True):
  """Returns a mapper from text options to the Ipv6AccessType enum.

  Args:
    messages: The message module.
    hidden: Whether the flag should be hidden in the choice_arg
  """

  help_text = """
Sets the IPv6 access type for the subnet created by GKE.

IPV6_ACCESS_TYPE must be one of:

  internal
    Creates a subnet with INTERNAL IPv6 access type.

  external
    Default value. Creates a subnet with EXTERNAL IPv6 access type.

  $ gcloud container clusters create \
      --ipv6-access-type=internal
  $ gcloud container clusters create \
      --ipv6-access-type=external
"""
  return arg_utils.ChoiceEnumMapper(
      '--ipv6-access-type',
      messages.IPAllocationPolicy.Ipv6AccessTypeValueValuesEnum,
      _GetIpv6AccessTypeCustomMappings(),
      hidden=hidden,
      help_str=help_text,
  )


def _GetBinauthzEvaluationModeCustomMappings():
  return {
      'DISABLED': 'disabled',
      'PROJECT_SINGLETON_POLICY_ENFORCE': 'project-singleton-policy-enforce',
      'POLICY_BINDINGS': 'policy-bindings',
      'POLICY_BINDINGS_AND_PROJECT_SINGLETON_POLICY_ENFORCE': (
          'policy-bindings-and-project-singleton-policy-enforce'
      ),
  }


def GetBinauthzEvaluationModeMapper(messages, hidden=False):
  """Returns a mapper from text options to the evaluation mode enum.

  Args:
    messages: The message module.
    hidden: Whether the flag should be hidden in the choice_arg
  """
  return arg_utils.ChoiceEnumMapper(
      '--binauthz-evaluation-mode',
      messages.BinaryAuthorization.EvaluationModeValueValuesEnum,
      _GetBinauthzEvaluationModeCustomMappings(),
      hidden=hidden,
      help_str='',
  )


def HasUnknownKeys(actual, known):
  if not actual:
    return
  if set(actual.keys()) - known:
    return 'following names are not recognised: {0}'.format(
        ' '.join(set(actual.keys()) - known)
    )


def ValidateAutoprovisioningConfigFile(nap_config_file):
  """Load and Validate Autoprovisioning configuration from YAML/JSON file.

  Args:
    nap_config_file: The YAML/JSON string that contains sysctl and kubelet
      options.

  Raises:
    Error: when there's any errors on parsing the YAML/JSON system config
    or wrong name are present.
  """

  try:
    nap_config = yaml.load(nap_config_file)
  except yaml.YAMLParseError as e:
    raise AutoprovisioningConfigError(
        'autoprovisioning config file is not valid YAML/JSON: {0}'.format(e)
    )
  if not nap_config:
    raise AutoprovisioningConfigError(
        'autoprovisioning config file cannot be empty'
    )
  nap_params = {
      'resourceLimits',
      'serviceAccount',
      'scopes',
      'upgradeSettings',
      'management',
      'autoprovisioningLocations',
      'minCpuPlatform',
      'imageType',
      'bootDiskKmsKey',
      'diskSizeGb',
      'diskType',
      'shieldedInstanceConfig',
  }
  err = HasUnknownKeys(nap_config, nap_params)
  if err:
    raise AutoprovisioningConfigError(err)

  if nap_config.get('upgradeSettings'):
    upgrade_settings_params = {'maxSurgeUpgrade', 'maxUnavailableUpgrade'}
    err = HasUnknownKeys(
        nap_config.get('upgradeSettings'), upgrade_settings_params
    )
    if err:
      raise AutoprovisioningConfigError(err)

  if nap_config.get('management'):
    node_management_params = {'autoUpgrade', 'autoRepair'}
    err = HasUnknownKeys(nap_config.get('management'), node_management_params)
    if err:
      raise AutoprovisioningConfigError(err)

  if nap_config.get('shieldedInstanceConfig'):
    shielded_params = {'enableSecureBoot', 'enableIntegrityMonitoring'}
    err = HasUnknownKeys(
        nap_config.get('shieldedInstanceConfig'), shielded_params
    )
    if err:
      raise AutoprovisioningConfigError(err)


def CheckForContainerFileSystemApiEnablementWithPrompt(project):
  """Checks if the Container File System API is enabled."""
  service_name = 'containerfilesystem.googleapis.com'
  try:
    if not enable_api.IsServiceEnabled(project, service_name):
      log.warning(
          'Container File System API (containerfilesystem.googleapis.com) has'
          ' not been enabled on the project. '
          'Please enable it for image streaming to fully work. '
          'For additional details, please refer to'
          ' https://cloud.google.com/kubernetes-engine/docs/how-to/image-streaming#requirements'
      )
  except (
      exceptions.GetServicePermissionDeniedException,
      apitools_exceptions.HttpError,
  ):
    log.warning(
        'Failed to check if Container File System API'
        ' (containerfilesystem.googleapis.com) has been enabled. '
        'Please make sure to enable it for image streaming to work. '
        'For additional details, please refer to'
        ' https://cloud.google.com/kubernetes-engine/docs/how-to/image-streaming#requirements'
    )


def LoadSoleTenantConfigFromNodeAffinityYaml(affinities_yaml, messages):
  """Loads json/yaml node affinities from yaml file contents."""

  if not affinities_yaml:
    raise Error(
        'No node affinity labels specified. You must specify at least one '
        'label to create a sole tenancy instance.'
    )

  if not yaml.list_like(affinities_yaml):
    raise Error('Node affinities must be specified as JSON/YAML list')

  node_affinities = []
  for affinity in affinities_yaml:
    node_affinity = None
    if not affinity:  # Catches None and empty dicts
      raise Error('Empty list item in JSON/YAML file.')
    try:
      node_affinity = encoding.PyValueToMessage(messages.NodeAffinity, affinity)
    except Exception as e:  # pylint: disable=broad-except
      raise Error(e)
    if not node_affinity.key:
      raise Error('A key must be specified for every node affinity label.')
    if node_affinity.all_unrecognized_fields():
      raise Error(
          'Key [{0}] has invalid field formats for: {1}'.format(
              node_affinity.key, node_affinity.all_unrecognized_fields()
          )
      )
    node_affinities.append(node_affinity)

  return messages.SoleTenantConfig(nodeAffinities=node_affinities)


def _IsGoogleInternalUser():
  """Returns a bool noting if User is a Googler."""
  email = properties.VALUES.core.account.Get()
  return email is not None and email.lower().endswith('@google.com')


def _GenerateIamToken() -> str:
  """Generates an IAM token for the current user, if the user is a Googler.

  The IAM token consists of three concatenated strings:
  1. The `iam-` prefix.
  2. The token associated with the credentials from the active account.
  3. The authorization token stored in the auth.authorization_token_file
     property.

  Returns:
    The IAM token for the current user.

  Raises:
    Error: if the user is not a Googler.
  """
  if not _IsGoogleInternalUser():
    raise Error(
        'IAM tokens are only supported for internal users. Please use a '
        'Google account.'
    )

  cred = c_store.Load(use_google_auth=True, allow_account_impersonation=False)
  auth_token_file = properties.VALUES.auth.authorization_token_file.Get(
      required=True
  )
  auth_token = file_utils.ReadFileContents(auth_token_file)

  return f'iam-{cred.token}^{auth_token}'
