# Copyright 2015 Google Inc. All Rights Reserved.
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
"""Api client adapter containers commands."""
from collections import deque
from os import linesep
import time

from apitools.base.py import exceptions as apitools_exceptions
from apitools.base.py import http_wrapper

from googlecloudsdk.api_lib.compute import constants
from googlecloudsdk.api_lib.container import util
from googlecloudsdk.api_lib.util import apis as core_apis
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources as cloud_resources
from googlecloudsdk.core.console import progress_tracker

WRONG_ZONE_ERROR_MSG = """\
{error}
Could not find [{name}] in [{wrong_zone}].
Did you mean [{name}] in [{zone}]?"""

NO_SUCH_CLUSTER_ERROR_MSG = """\
{error}
No cluster named '{name}' in {project}."""

NO_SUCH_NODE_POOL_ERROR_MSG = """\
No node pool named '{name}' in {cluster}."""

NO_NODE_POOL_SELECTED_ERROR_MSG = """\
Please specify one of the following node pools:
"""

MISMATCH_AUTHORIZED_NETWORKS_ERROR_MSG = """\
Cannot use --master-authorized-networks \
if --enable-master-authorized-networks is not \
specified."""

NO_SUCH_LABEL_ERROR_MSG = """\
No label named '{name}' found on cluster '{cluster}'."""

NO_LABELS_ON_CLUSTER_ERROR_MSG = """\
Cluster '{cluster}' has no labels to remove."""

SERVICES_IPV4_CIDR_ALPHA_ONLY_ERROR_MSG = """\
Cannot use --services-ipv4-cidr without --enable-ip-alias and --enable_kubernetes_alpha.
"""

CREATE_SUBNETWORK_ALPHA_ONLY_ERROR_MSG = """\
Cannot use --create-subnetwork without --enable-ip-alias and --enable_kubernetes_alpha.
"""

ENABLE_IP_ALIAS_ALPHA_ONLY_ERROR_MSG = """\
Only alpha clusters (--enable_kubernetes_alpha) can use --enable-ip-alias.
"""

CREATE_SUBNETWORK_INVALID_KEY_ERROR_MSG = """\
Invalid key '{key}' for --create-subnetwork (must be one of 'name', 'range').
"""

CREATE_SUBNETWORK_WITH_SUBNETWORK_ERROR_MSG = """\
Cannot specify both '--subnetwork' and '--create-subnetwork' at the same time.
"""

MAX_NODES_PER_POOL = 1000


def CheckResponse(response):
  """Wrap http_wrapper.CheckResponse to skip retry on 503."""
  if response.status_code == 503:
    raise apitools_exceptions.HttpError.FromResponse(response)
  return http_wrapper.CheckResponse(response)


def NewAPIAdapter(api_version):
  if api_version is 'v1alpha1':
    return NewV1Alpha1APIAdapter()
  else:
    return NewV1APIAdapter()


def NewV1APIAdapter():
  return InitAPIAdapter('v1', V1Adapter)


def NewV1Alpha1APIAdapter():
  return InitAPIAdapter('v1alpha1', V1Alpha1Adapter)


def InitAPIAdapter(api_version, adapter):
  """Initialize an api adapter.

  Args:
    api_version: the api version we want.
    adapter: the api adapter constructor.
  Returns:
    APIAdapter object.
  """

  api_client = core_apis.GetClientInstance('container', api_version)
  api_client.check_response_func = CheckResponse
  messages = core_apis.GetMessagesModule('container', api_version)

  api_compute_client = core_apis.GetClientInstance('compute', 'v1')
  api_compute_client.check_response_func = CheckResponse
  compute_messages = core_apis.GetMessagesModule('compute', 'v1')

  registry = cloud_resources.REGISTRY.Clone()
  registry.RegisterApiByName('container', api_version)
  registry.RegisterApiByName('compute', 'v1')

  return adapter(registry, api_client, messages, api_compute_client,
                 compute_messages)


_REQUIRED_SCOPES = (
    constants.SCOPES['compute-rw'] + constants.SCOPES['storage-ro'])

_ENDPOINTS_SCOPES = (
    constants.SCOPES['service-control'] +
    constants.SCOPES['service-management'])


def ExpandScopeURIs(scopes):
  """Expand scope names to the fully qualified uris.

  Args:
    scopes: [str,] list of scope names. Can be short names ('compute-rw')
      or full urls ('https://www.googleapis.com/auth/compute')

  Returns:
    list of str, full urls for recognized scopes.

  Raises:
    util.Error, if any scope provided is not recognized. See SCOPES in
        cloud/sdk/compute/lib/constants.py.
  """

  scope_uris = []
  for scope in scopes:
    # Expand any scope aliases (like 'storage-rw') that the user provided
    # to their official URL representation.
    expanded = constants.SCOPES.get(scope, [scope])
    scope_uris.extend(expanded)
  return scope_uris


class CreateClusterOptions(object):

  def __init__(self,
               node_machine_type=None,
               node_source_image=None,
               node_disk_size_gb=None,
               scopes=None,
               enable_cloud_endpoints=None,
               num_nodes=None,
               additional_zones=None,
               user=None,
               password=None,
               cluster_version=None,
               network=None,
               cluster_ipv4_cidr=None,
               enable_cloud_logging=None,
               enable_cloud_monitoring=None,
               subnetwork=None,
               disable_addons=None,
               local_ssd_count=None,
               tags=None,
               node_labels=None,
               enable_autoscaling=None,
               min_nodes=None,
               max_nodes=None,
               image_type=None,
               max_nodes_per_pool=None,
               enable_kubernetes_alpha=None,
               preemptible=None,
               enable_autorepair=None,
               enable_autoupgrade=None,
               service_account=None,
               enable_master_authorized_networks=None,
               master_authorized_networks=None,
               enable_legacy_authorization=None,
               labels=None,
               disk_type=None,
               enable_network_policy=None,
               services_ipv4_cidr=None,
               enable_ip_alias=None,
               create_subnetwork=None,
               accelerators=None):
    self.node_machine_type = node_machine_type
    self.node_source_image = node_source_image
    self.node_disk_size_gb = node_disk_size_gb
    self.scopes = scopes
    self.enable_cloud_endpoints = enable_cloud_endpoints
    self.num_nodes = num_nodes
    self.additional_zones = additional_zones
    self.user = user
    self.password = password
    self.cluster_version = cluster_version
    self.network = network
    self.cluster_ipv4_cidr = cluster_ipv4_cidr
    self.enable_cloud_logging = enable_cloud_logging
    self.enable_cloud_monitoring = enable_cloud_monitoring
    self.subnetwork = subnetwork
    self.disable_addons = disable_addons
    self.local_ssd_count = local_ssd_count
    self.tags = tags
    self.node_labels = node_labels
    self.enable_autoscaling = enable_autoscaling
    self.min_nodes = min_nodes
    self.max_nodes = max_nodes
    self.image_type = image_type
    self.max_nodes_per_pool = max_nodes_per_pool
    self.enable_kubernetes_alpha = enable_kubernetes_alpha
    self.preemptible = preemptible
    self.enable_autorepair = enable_autorepair
    self.enable_autoupgrade = enable_autoupgrade
    self.service_account = service_account
    self.enable_master_authorized_networks = enable_master_authorized_networks
    self.master_authorized_networks = master_authorized_networks
    self.enable_legacy_authorization = enable_legacy_authorization
    self.enable_network_policy = enable_network_policy
    self.labels = labels
    self.disk_type = disk_type
    self.services_ipv4_cidr = services_ipv4_cidr
    self.enable_ip_alias = enable_ip_alias
    self.create_subnetwork = create_subnetwork
    self.accelerators = accelerators


INGRESS = 'HttpLoadBalancing'
HPA = 'HorizontalPodAutoscaling'


class UpdateClusterOptions(object):

  def __init__(self,
               version=None,
               update_master=None,
               update_nodes=None,
               node_pool=None,
               monitoring_service=None,
               disable_addons=None,
               enable_autoscaling=None,
               min_nodes=None,
               max_nodes=None,
               image_type=None,
               locations=None,
               enable_master_authorized_networks=None,
               master_authorized_networks=None):
    self.version = version
    self.update_master = bool(update_master)
    self.update_nodes = bool(update_nodes)
    self.node_pool = node_pool
    self.monitoring_service = monitoring_service
    self.disable_addons = disable_addons
    self.enable_autoscaling = enable_autoscaling
    self.min_nodes = min_nodes
    self.max_nodes = max_nodes
    self.image_type = image_type
    self.locations = locations
    self.enable_master_authorized_networks = enable_master_authorized_networks
    self.master_authorized_networks = master_authorized_networks


class SetMasterAuthOptions(object):
  SET_PASSWORD = 'SetPassword'
  GENERATE_PASSWORD = 'GeneratePassword'

  def __init__(self,
               action=None,
               password=None):
    self.action = action
    self.password = password


class SetNetworkPolicyOptions(object):

  def __init__(self, enabled):
    self.enabled = enabled


class CreateNodePoolOptions(object):

  def __init__(self,
               machine_type=None,
               disk_size_gb=None,
               scopes=None,
               enable_cloud_endpoints=None,
               num_nodes=None,
               local_ssd_count=None,
               tags=None,
               node_labels=None,
               enable_autoscaling=None,
               max_nodes=None,
               min_nodes=None,
               image_type=None,
               preemptible=None,
               enable_autorepair=None,
               enable_autoupgrade=None,
               service_account=None,
               disk_type=None,
               accelerators=None):
    self.machine_type = machine_type
    self.disk_size_gb = disk_size_gb
    self.scopes = scopes
    self.enable_cloud_endpoints = enable_cloud_endpoints
    self.num_nodes = num_nodes
    self.local_ssd_count = local_ssd_count
    self.tags = tags
    self.node_labels = node_labels
    self.enable_autoscaling = enable_autoscaling
    self.max_nodes = max_nodes
    self.min_nodes = min_nodes
    self.image_type = image_type
    self.preemptible = preemptible
    self.enable_autorepair = enable_autorepair
    self.enable_autoupgrade = enable_autoupgrade
    self.service_account = service_account
    self.disk_type = disk_type
    self.accelerators = accelerators


class UpdateNodePoolOptions(object):

  def __init__(self,
               enable_autorepair=None,
               enable_autoupgrade=None):
    self.enable_autorepair = enable_autorepair
    self.enable_autoupgrade = enable_autoupgrade


class APIAdapter(object):
  """Handles making api requests in a version-agnostic way."""

  def __init__(self, registry, client, messages, compute_client,
               compute_messages):
    self.registry = registry
    self.client = client
    self.messages = messages
    self.compute_client = compute_client
    self.compute_messages = compute_messages

  def ParseCluster(self, name, location):
    if not location:
      location = properties.VALUES.compute.zone.GetOrFail
    # TODO(b/63383536): Migrate to container.projects.locations.clusters when
    # apiserver supports it.
    return self.registry.Parse(
        name,
        params={
            'projectId': properties.VALUES.core.project.GetOrFail,
            'zone': location,
        },
        collection='container.projects.zones.clusters')

  def PrintClusters(self, clusters):
    raise NotImplementedError('PrintClusters is not overriden')

  def PrintOperations(self, operations):
    raise NotImplementedError('PrintOperations is not overriden')

  def PrintNodePools(self, node_pools):
    raise NotImplementedError('PrintNodePools is not overriden')

  def ParseOperation(self, operation_id, location=None):
    if not location:
      location = properties.VALUES.compute.zone.GetOrFail
    # TODO(b/63383536): Migrate to container.projects.locations.operations when
    # apiserver supports it.
    return self.registry.Parse(
        operation_id,
        params={
            'projectId': properties.VALUES.core.project.GetOrFail,
            'zone': location,
        },
        collection='container.projects.zones.operations')

  def ParseNodePool(self, node_pool_id, location):
    if not location:
      location = properties.VALUES.compute.zone.GetOrFail
    # TODO(b/63383536): Migrate to container.projects.locations.nodePools when
    # apiserver supports it.
    return self.registry.Parse(
        node_pool_id,
        params={
            'projectId': properties.VALUES.core.project.GetOrFail,
            'clusterId': properties.VALUES.container.cluster.GetOrFail,
            'zone': location,
        },
        collection='container.projects.zones.clusters.nodePools')

  def ParseIGM(self, igm_id):
    return self.registry.Parse(igm_id,
                               collection='compute.instanceGroupManagers')

  def GetCluster(self, cluster_ref):
    """Get a running cluster.

    Args:
      cluster_ref: cluster Resource to describe.
    Returns:
      Cluster message.
    Raises:
      Error: if cluster cannot be found.
    """
    try:
      return self.client.projects_zones_clusters.Get(
          self.messages.ContainerProjectsZonesClustersGetRequest(
              projectId=cluster_ref.projectId,
              zone=cluster_ref.zone,
              clusterId=cluster_ref.clusterId))
    except apitools_exceptions.HttpError as error:
      api_error = exceptions.HttpException(error, util.HTTP_ERROR_FORMAT)
      if api_error.payload.status_code != 404:
        raise api_error

    # Cluster couldn't be found, maybe user got zone wrong?
    try:
      clusters = self.ListClusters(cluster_ref.projectId).clusters
    except apitools_exceptions.HttpError as error:
      raise exceptions.HttpException(error, util.HTTP_ERROR_FORMAT)
    for cluster in clusters:
      if cluster.name == cluster_ref.clusterId:
        # User likely got zone wrong.
        raise util.Error(WRONG_ZONE_ERROR_MSG.format(
            error=api_error,
            name=cluster_ref.clusterId,
            wrong_zone=self.Zone(cluster_ref),
            zone=cluster.zone))
    # Couldn't find a cluster with that name.
    raise util.Error(NO_SUCH_CLUSTER_ERROR_MSG.format(
        error=api_error,
        name=cluster_ref.clusterId,
        project=cluster_ref.projectId))

  def FindNodePool(self, cluster, pool_name=None):
    """Find the node pool with the given name in the cluster."""
    msg = ''
    if pool_name:
      for np in cluster.nodePools:
        if np.name == pool_name:
          return np
      msg = NO_SUCH_NODE_POOL_ERROR_MSG.format(cluster=cluster.name,
                                               name=pool_name) + linesep
    elif len(cluster.nodePools) == 1:
      return cluster.nodePools[0]
    # Couldn't find a node pool with that name or a node pool was not specified.
    msg += NO_NODE_POOL_SELECTED_ERROR_MSG + linesep.join(
        [np.name for np in cluster.nodePools])
    raise util.Error(msg)

  def GetOperation(self, operation_ref):
    return self.client.projects_zones_operations.Get(
        self.messages.ContainerProjectsZonesOperationsGetRequest(
            projectId=operation_ref.projectId,
            zone=operation_ref.zone,
            operationId=operation_ref.operationId))

  def GetComputeOperation(self, project, zone, operation_id):
    req = self.compute_messages.ComputeZoneOperationsGetRequest(
        operation=operation_id,
        project=project,
        zone=zone)
    return self.compute_client.zoneOperations.Get(req)

  def WaitForOperation(self, operation_ref, message,
                       timeout_s=1200, poll_period_s=5):
    """Poll container Operation until its status is done or timeout reached.

    Args:
      operation_ref: operation resource.
      message: str, message to display to user while polling.
      timeout_s: number, seconds to poll with retries before timing out.
      poll_period_s: number, delay in seconds between requests.

    Returns:
      Operation: the return value of the last successful operations.get
      request.

    Raises:
      Error: if the operation times out or finishes with an error.
    """
    detail_message = None
    with progress_tracker.ProgressTracker(message, autotick=True,
                                          detail_message_callback=
                                          lambda: detail_message):
      start_time = time.clock()
      while timeout_s > (time.clock() - start_time):
        try:
          operation = self.GetOperation(operation_ref)
          if self.IsOperationFinished(operation):
            # Success!
            log.info('Operation %s succeeded after %.3f seconds',
                     operation, (time.clock() - start_time))
            break
          detail_message = operation.detail
        except apitools_exceptions.HttpError as error:
          log.debug('GetOperation failed: %s', error)
          # Keep trying until we timeout in case error is transient.
          # TODO(b/36050880): add additional backoff if server is returning 500s
        time.sleep(poll_period_s)
    if not self.IsOperationFinished(operation):
      log.err.Print('Timed out waiting for operation {0}'.format(operation))
      raise util.Error(
          'Operation [{0}] is still running'.format(operation))
    if self.GetOperationError(operation):
      raise util.Error('Operation [{0}] finished with error: {1}'.format(
          operation, self.GetOperationError(operation)))

    return operation

  def IsComputeOperationFinished(self, operation):
    return (operation.status ==
            self.compute_messages.Operation.StatusValueValuesEnum.DONE)

  def WaitForComputeOperations(self, project, zone, operation_ids, message,
                               timeout_s=1200, poll_period_s=5):
    """Poll Compute Operations until their status is done or timeout reached.

    Args:
      project: project on which the operation is performed
      zone: zone on which the operation is performed
      operation_ids: list/set of ids of the compute operations to wait for
      message: str, message to display to user while polling.
      timeout_s: number, seconds to poll with retries before timing out.
      poll_period_s: number, delay in seconds between requests.

    Returns:
      Operations: list of the last successful operations.getrequest for each op.

    Raises:
      Error: if the operation times out or finishes with an error.
    """
    operation_ids = deque(operation_ids)
    operations = {}
    errors = []
    with progress_tracker.ProgressTracker(message, autotick=True):
      start_time = time.clock()
      ops_to_retry = []
      while timeout_s > (time.clock() - start_time) and operation_ids:
        op_id = operation_ids.popleft()
        try:
          operation = self.GetComputeOperation(project, zone, op_id)
          operations[op_id] = operation
          if not self.IsComputeOperationFinished(operation):
            # Operation is still in progress.
            ops_to_retry.append(op_id)
            continue

          log.debug('Operation %s succeeded after %.3f seconds', operation,
                    (time.clock() - start_time))
          error = self.GetOperationError(operation)
          if error:
            # Operation Failed!
            msg = 'Operation [{0}] finished with error: {1}'.format(op_id,
                                                                    error)
            log.debug(msg)
            errors.append(msg)
        except apitools_exceptions.HttpError as error:
          log.debug('GetComputeOperation failed: %s', error)
          # Keep trying until we timeout in case error is transient.
          # TODO(b/36050235): add additional backoff if server is returning 500s
        if not operation_ids and ops_to_retry:
          operation_ids = deque(ops_to_retry)
          ops_to_retry = []
          time.sleep(poll_period_s)

    operation_ids.extend(ops_to_retry)
    for op_id in operation_ids:
      errors.append('Operation [{0}] is still running'.format(op_id))
    if errors:
      raise util.Error(linesep.join(errors))

    return operations.values()

  def Zone(self, cluster_ref):
    return cluster_ref.zone

  def Version(self, cluster):
    return cluster.currentMasterVersion

  def CreateClusterCommon(self, cluster_ref, options):
    """Returns a CreateCluster operation."""
    node_config = self.messages.NodeConfig()
    if options.node_machine_type:
      node_config.machineType = options.node_machine_type
    if options.node_disk_size_gb:
      node_config.diskSizeGb = options.node_disk_size_gb
    if options.disk_type:
      node_config.diskType = options.disk_type
    if options.node_source_image:
      raise util.Error('cannot specify node source image in container v1 api')
    scope_uris = ExpandScopeURIs(options.scopes)
    if options.enable_cloud_endpoints:
      scope_uris += _ENDPOINTS_SCOPES
    node_config.oauthScopes = sorted(set(scope_uris + _REQUIRED_SCOPES))

    if options.local_ssd_count:
      node_config.localSsdCount = options.local_ssd_count

    if options.tags:
      node_config.tags = options.tags
    else:
      node_config.tags = []

    if options.image_type:
      node_config.imageType = options.image_type

    _AddNodeLabelsToNodeConfig(node_config, options)

    if options.preemptible:
      node_config.preemptible = options.preemptible

    if options.service_account:
      node_config.serviceAccount = options.service_account

    if options.accelerators is not None:
      type_name = options.accelerators['type']
      # Accelerator count defaults to 1.
      count = int(options.accelerators.get('count', 1))
      node_config.accelerators = [
          self.messages.AcceleratorConfig(acceleratorType=type_name,
                                          acceleratorCount=count)
      ]

    max_nodes_per_pool = options.max_nodes_per_pool or MAX_NODES_PER_POOL
    pools = (options.num_nodes + max_nodes_per_pool - 1) / max_nodes_per_pool
    if pools == 1:
      pool_names = ['default-pool']  # pool consistency with server default
    else:
      # default-pool-0, -1, ...
      pool_names = ['default-pool-{0}'.format(i) for i in range(0, pools)]

    pools = []
    per_pool = (options.num_nodes + len(pool_names) - 1) / len(pool_names)
    to_add = options.num_nodes
    for name in pool_names:
      nodes = per_pool if (to_add > per_pool) else to_add
      autoscaling = None
      if options.enable_autoscaling:
        autoscaling = self.messages.NodePoolAutoscaling(
            enabled=options.enable_autoscaling,
            minNodeCount=options.min_nodes,
            maxNodeCount=options.max_nodes)
      pools.append(self.messages.NodePool(
          name=name,
          initialNodeCount=nodes,
          config=node_config,
          autoscaling=autoscaling,
          management=self._GetNodeManagement(options)))
      to_add -= nodes

    cluster = self.messages.Cluster(
        name=cluster_ref.clusterId,
        nodePools=pools,
        masterAuth=self.messages.MasterAuth(username=options.user,
                                            password=options.password))
    if options.additional_zones:
      cluster.locations = sorted([cluster_ref.zone] + options.additional_zones)
    if options.cluster_version:
      cluster.initialClusterVersion = options.cluster_version
    if options.network:
      cluster.network = options.network
    if options.cluster_ipv4_cidr:
      cluster.clusterIpv4Cidr = options.cluster_ipv4_cidr
    if not options.enable_cloud_logging:
      cluster.loggingService = 'none'
    if not options.enable_cloud_monitoring:
      cluster.monitoringService = 'none'
    if options.subnetwork:
      cluster.subnetwork = options.subnetwork
    if options.disable_addons:
      addons = self._AddonsConfig(
          disable_ingress=INGRESS in options.disable_addons or None,
          disable_hpa=HPA in options.disable_addons or None)
      cluster.addonsConfig = addons
    if options.enable_master_authorized_networks:
      authorized_networks = self.messages.MasterAuthorizedNetworks(
          enabled=options.enable_master_authorized_networks)
      if options.master_authorized_networks:
        for network in options.master_authorized_networks:
          authorized_networks.cidrs.append(self.messages.CIDR(network=network))
      cluster.masterAuthorizedNetworks = authorized_networks
    elif options.master_authorized_networks:
      # Raise error if use --master-authorized-networks without
      # --enable-master-authorized-networks.
      raise util.Error(MISMATCH_AUTHORIZED_NETWORKS_ERROR_MSG)

    if options.enable_kubernetes_alpha:
      cluster.enableKubernetesAlpha = options.enable_kubernetes_alpha

    if options.enable_legacy_authorization is not None:
      cluster.legacyAbac = self.messages.LegacyAbac(
          enabled=bool(options.enable_legacy_authorization))

    # Only Calico is currently supported as a network policy provider.
    if options.enable_network_policy:
      cluster.networkPolicy = self.messages.NetworkPolicy(
          enabled=options.enable_network_policy,
          provider=self.messages.NetworkPolicy.ProviderValueValuesEnum.CALICO)

    if options.labels is not None:
      labels = self.messages.Cluster.ResourceLabelsValue()
      props = []
      for k, v in sorted(options.labels.iteritems()):
        props.append(labels.AdditionalProperty(key=k, value=v))
      labels.additionalProperties = props
      cluster.resourceLabels = labels

    if options.enable_kubernetes_alpha:
      if not options.enable_ip_alias and options.services_ipv4_cidr:
        raise util.Error(SERVICES_IPV4_CIDR_ALPHA_ONLY_ERROR_MSG)
      if not options.enable_ip_alias and options.create_subnetwork:
        raise util.Error(CREATE_SUBNETWORK_ALPHA_ONLY_ERROR_MSG)
      if options.create_subnetwork and options.subnetwork:
        raise util.Error(CREATE_SUBNETWORK_WITH_SUBNETWORK_ERROR_MSG)

      if options.enable_ip_alias:
        subnetwork_name = None
        node_ipv4_cidr = None

        if options.create_subnetwork:
          for key in options.create_subnetwork:
            if key not in ['name', 'range']:
              raise util.Error(
                  CREATE_SUBNETWORK_INVALID_KEY_ERROR_MSG.format(key=key))
          subnetwork_name = options.create_subnetwork.get('name', None)
          node_ipv4_cidr = options.create_subnetwork.get('range', None)
        policy = self.messages.IPAllocationPolicy(
            useIpAliases=options.enable_ip_alias,
            # For V1, create_subnetwork is always true.
            createSubnetwork=True,
            subnetworkName=subnetwork_name,
            clusterIpv4Cidr=options.cluster_ipv4_cidr,
            nodeIpv4Cidr=node_ipv4_cidr,
            servicesIpv4Cidr=options.services_ipv4_cidr)
        cluster.clusterIpv4Cidr = None
        cluster.ipAllocationPolicy = policy
    else:
      if options.enable_ip_alias:
        raise util.Error(ENABLE_IP_ALIAS_ALPHA_ONLY_ERROR_MSG)
      if options.services_ipv4_cidr:
        raise util.Error(SERVICES_IPV4_CIDR_ALPHA_ONLY_ERROR_MSG)
      if options.create_subnetwork:
        raise util.Error(CREATE_SUBNETWORK_ALPHA_ONLY_ERROR_MSG)
    return cluster

  def CreateCluster(self, cluster_ref, options):
    raise NotImplementedError('CreateCluster is not overriden')

  def UpdateClusterCommon(self, options):
    """Returns an UpdateCluster operation."""
    if not options.version:
      options.version = '-'
    if options.update_nodes:
      update = self.messages.ClusterUpdate(
          desiredNodeVersion=options.version,
          desiredNodePoolId=options.node_pool,
          desiredImageType=options.image_type)
    elif options.update_master:
      update = self.messages.ClusterUpdate(
          desiredMasterVersion=options.version)
    elif options.monitoring_service:
      update = self.messages.ClusterUpdate(
          desiredMonitoringService=options.monitoring_service)
    elif options.disable_addons:
      addons = self._AddonsConfig(
          disable_ingress=options.disable_addons.get(INGRESS),
          disable_hpa=options.disable_addons.get(HPA))
      update = self.messages.ClusterUpdate(desiredAddonsConfig=addons)
    elif options.enable_autoscaling is not None:
      # For update, we can either enable or disable.
      autoscaling = self.messages.NodePoolAutoscaling(
          enabled=options.enable_autoscaling)
      if options.enable_autoscaling:
        autoscaling.minNodeCount = options.min_nodes
        autoscaling.maxNodeCount = options.max_nodes
      update = self.messages.ClusterUpdate(
          desiredNodePoolId=options.node_pool,
          desiredNodePoolAutoscaling=autoscaling)
    elif options.locations:
      update = self.messages.ClusterUpdate(desiredLocations=options.locations)
    elif options.enable_master_authorized_networks is not None:
      # For update, we can either enable or disable.
      authorized_networks = self.messages.MasterAuthorizedNetworks(
          enabled=options.enable_master_authorized_networks)
      if options.master_authorized_networks:
        for network in options.master_authorized_networks:
          authorized_networks.cidrs.append(self.messages.CIDR(network=network))
      update = self.messages.ClusterUpdate(
          desiredMasterAuthorizedNetworks=authorized_networks)
    if (options.master_authorized_networks
        and not options.enable_master_authorized_networks):
      # Raise error if use --master-authorized-networks without
      # --enable-master-authorized-networks.
      raise util.Error(MISMATCH_AUTHORIZED_NETWORKS_ERROR_MSG)
    return update

  def UpdateCluster(self, cluster_ref, options):
    raise NotImplementedError('UpdateCluster is not overriden')

  def SetLegacyAuthorization(self, cluster_ref, enable_legacy_authorization):
    raise NotImplementedError('SetLegacyAuthorization is not overriden')

  def _AddonsConfig(self, disable_ingress=None, disable_hpa=None):
    addons = self.messages.AddonsConfig()
    if disable_ingress is not None:
      addons.httpLoadBalancing = self.messages.HttpLoadBalancing(
          disabled=bool(disable_ingress))
    if disable_hpa is not None:
      addons.horizontalPodAutoscaling = self.messages.HorizontalPodAutoscaling(
          disabled=bool(disable_hpa))
    return addons

  def SetNetworkPolicyCommon(self, options):
    """Returns a SetNetworkPolicy operation."""
    return self.messages.NetworkPolicy(
        enabled=options.enabled,
        # Only Calico is currently supported as a network policy provider.
        provider=self.messages.NetworkPolicy.ProviderValueValuesEnum.CALICO)

  def SetNetworkPolicy(self, cluster_ref, options):
    raise NotImplementedError('SetNetworkPolicy is not overriden')

  def SetMasterAuthCommon(self, options):
    """Returns a SetMasterAuth action."""
    update = self.messages.MasterAuth(password=options.password)
    if options.action == SetMasterAuthOptions.SET_PASSWORD:
      action = (self.messages.SetMasterAuthRequest.
                ActionValueValuesEnum.SET_PASSWORD)
    else:
      action = (self.messages.SetMasterAuthRequest.
                ActionValueValuesEnum.GENERATE_PASSWORD)
    return update, action

  def SetMasterAuth(self, cluster_ref, options):
    raise NotImplementedError('SetMasterAuth is not overriden')

  def StartIpRotation(self, cluster_ref):
    raise NotImplementedError('StartIpRotation is not overriden')

  def CompleteIpRotation(self, cluster_ref):
    raise NotImplementedError('CompleteIpRotation is not overriden')

  def DeleteCluster(self, cluster_ref):
    operation = self.client.projects_zones_clusters.Delete(
        self.messages.ContainerProjectsZonesClustersDeleteRequest(
            clusterId=cluster_ref.clusterId,
            zone=cluster_ref.zone,
            projectId=cluster_ref.projectId))
    return self.ParseOperation(operation.name, cluster_ref.zone)

  def ListClusters(self, project, zone=None):
    if not zone:
      zone = '-'
    req = self.messages.ContainerProjectsZonesClustersListRequest(
        projectId=project, zone=zone)
    return self.client.projects_zones_clusters.List(req)

  def CreateNodePoolCommon(self, node_pool_ref, options):
    """Returns a CreateNodePool operation."""
    node_config = self.messages.NodeConfig()
    if options.machine_type:
      node_config.machineType = options.machine_type
    if options.disk_size_gb:
      node_config.diskSizeGb = options.disk_size_gb
    if options.disk_type:
      node_config.diskType = options.disk_type
    if options.image_type:
      node_config.imageType = options.image_type
    scope_uris = ExpandScopeURIs(options.scopes)
    if options.enable_cloud_endpoints:
      scope_uris += _ENDPOINTS_SCOPES
    node_config.oauthScopes = sorted(set(scope_uris + _REQUIRED_SCOPES))
    if options.local_ssd_count:
      node_config.localSsdCount = options.local_ssd_count
    if options.tags:
      node_config.tags = options.tags
    else:
      node_config.tags = []
    if options.service_account:
      node_config.serviceAccount = options.service_account

    if options.accelerators is not None:
      type_name = options.accelerators['type']
      # Accelerator count defaults to 1.
      count = int(options.accelerators.get('count', 1))
      node_config.accelerators = [
          self.messages.AcceleratorConfig(acceleratorType=type_name,
                                          acceleratorCount=count)
      ]

    _AddNodeLabelsToNodeConfig(node_config, options)

    if options.preemptible:
      node_config.preemptible = options.preemptible

    pool = self.messages.NodePool(
        name=node_pool_ref.nodePoolId,
        initialNodeCount=options.num_nodes,
        config=node_config,
        management=self._GetNodeManagement(options))

    if options.enable_autoscaling:
      pool.autoscaling = self.messages.NodePoolAutoscaling(
          enabled=options.enable_autoscaling,
          minNodeCount=options.min_nodes,
          maxNodeCount=options.max_nodes)
    return pool

  def CreateNodePool(self, node_pool_ref, options):
    raise NotImplementedError('CreateNodePool is not overriden')

  def ListNodePools(self, cluster_ref):
    req = self.messages.ContainerProjectsZonesClustersNodePoolsListRequest(
        projectId=cluster_ref.projectId, zone=cluster_ref.zone,
        clusterId=cluster_ref.clusterId)
    return self.client.projects_zones_clusters_nodePools.List(req)

  def GetNodePool(self, node_pool_ref):
    req = self.messages.ContainerProjectsZonesClustersNodePoolsGetRequest(
        projectId=node_pool_ref.projectId,
        zone=node_pool_ref.zone,
        clusterId=node_pool_ref.clusterId,
        nodePoolId=node_pool_ref.nodePoolId)
    return self.client.projects_zones_clusters_nodePools.Get(req)

  def UpdateNodePoolCommon(self, node_pool_ref, options):
    """Update a node pool.

    Args:
      node_pool_ref: node pool Resource to update.
      options: node pool update options
    Returns:
      Operation ref for node pool update operation.
    """
    pool = self.GetNodePool(node_pool_ref)
    node_management = pool.management
    if node_management is None:
      node_management = self.messages.NodeManagement()
    if options.enable_autorepair is not None:
      node_management.autoRepair = options.enable_autorepair
    if options.enable_autoupgrade is not None:
      node_management.autoUpgrade = options.enable_autoupgrade
    return node_management

  def UpdateNodePool(self, node_pool_ref, options):
    raise NotImplementedError('UpdateNodePool is not overriden')

  def DeleteNodePool(self, node_pool_ref):
    operation = self.client.projects_zones_clusters_nodePools.Delete(
        self.messages.ContainerProjectsZonesClustersNodePoolsDeleteRequest(
            clusterId=node_pool_ref.clusterId,
            zone=node_pool_ref.zone,
            projectId=node_pool_ref.projectId,
            nodePoolId=node_pool_ref.nodePoolId))
    return self.ParseOperation(operation.name, node_pool_ref.zone)

  def RollbackUpgrade(self, node_pool_ref):
    raise NotImplementedError('RollbackUpgrade is not overriden')

  def CancelOperation(self, op_ref):
    raise NotImplementedError('CancelOperation is not overriden')

  def IsRunning(self, cluster):
    return (cluster.status ==
            self.messages.Cluster.StatusValueValuesEnum.RUNNING)

  def GetOperationError(self, operation):
    return operation.statusMessage

  def ListOperations(self, project, zone=None):
    if not zone:
      zone = '-'
    req = self.messages.ContainerProjectsZonesOperationsListRequest(
        projectId=project, zone=zone)
    return self.client.projects_zones_operations.List(req)

  def IsOperationFinished(self, operation):
    return (operation.status ==
            self.messages.Operation.StatusValueValuesEnum.DONE)

  def GetServerConfig(self, project, zone):
    req = self.messages.ContainerProjectsZonesGetServerconfigRequest(
        projectId=project, zone=zone)
    return self.client.projects_zones.GetServerconfig(req)

  def ResizeCluster(self, project, zone, group_name, size):
    req = self.compute_messages.ComputeInstanceGroupManagersResizeRequest(
        instanceGroupManager=group_name,
        project=project,
        size=size,
        zone=zone)
    return self.compute_client.instanceGroupManagers.Resize(req)

  def _GetNodeManagement(self, options):
    """Gets a wrapper containing the options for how nodes are managed.

    Args:
      options: node management options

    Returns:
      A NodeManagement object that contains the options indicating how nodes
      are managed. This is currently quite simple, containing only two options.
      However, there are more options planned for node management.
    """
    if options.enable_autorepair is None and options.enable_autoupgrade is None:
      return None

    node_management = self.messages.NodeManagement()
    node_management.autoRepair = options.enable_autorepair
    node_management.autoUpgrade = options.enable_autoupgrade
    return node_management

  def UpdateLabelsCommon(self, cluster_ref, update_labels):
    """Update labels on a cluster.

    Args:
      cluster_ref: cluster to update.
      update_labels: labels to set.
    Returns:
      Operation ref for label set operation.
    """
    clus = None
    try:
      clus = self.client.projects_zones_clusters.Get(
          self.messages.ContainerProjectsZonesClustersGetRequest(
              projectId=cluster_ref.projectId,
              zone=cluster_ref.zone,
              clusterId=cluster_ref.clusterId))
    except apitools_exceptions.HttpError as error:
      api_error = exceptions.HttpException(error, util.HTTP_ERROR_FORMAT)
      if api_error.payload.status_code != 404:
        raise api_error

    labels = self.messages.SetLabelsRequest.ResourceLabelsValue()
    props = []
    for k, v in sorted(update_labels.iteritems()):
      props.append(labels.AdditionalProperty(key=k, value=v))
    labels.additionalProperties = props
    return labels, clus.labelFingerprint

  def UpdateLabels(self, cluster_ref, update_labels):
    raise NotImplementedError('UpdateLabels is not overriden')

  def RemoveLabelsCommon(self, cluster_ref, remove_labels):
    """Removes labels from a cluster.

    Args:
      cluster_ref: cluster to update.
      remove_labels: labels to remove.
    Returns:
      Operation ref for label set operation.
    """
    clus = None
    try:
      clus = self.client.projects_zones_clusters.Get(
          self.messages.ContainerProjectsZonesClustersGetRequest(
              projectId=cluster_ref.projectId,
              zone=cluster_ref.zone,
              clusterId=cluster_ref.clusterId))
    except apitools_exceptions.HttpError as error:
      api_error = exceptions.HttpException(error, util.HTTP_ERROR_FORMAT)
      if api_error.payload.status_code != 404:
        raise api_error

    clus_labels = {}
    if clus.resourceLabels:
      for item in clus.resourceLabels.additionalProperties:
        clus_labels[item.key] = str(item.value)

    # if clusLabels empty, nothing to do
    if not clus_labels:
      raise util.Error(NO_LABELS_ON_CLUSTER_ERROR_MSG.format(cluster=clus.name))

    for k in remove_labels:
      try:
        clus_labels.pop(k)
      except KeyError as error:
        # if at least one label not found on cluster, raise error
        raise util.Error(
            NO_SUCH_LABEL_ERROR_MSG.format(cluster=clus.name, name=k))

    labels = self.messages.SetLabelsRequest.ResourceLabelsValue()
    for k, v in sorted(clus_labels.iteritems()):
      labels.additionalProperties.append(
          labels.AdditionalProperty(key=k, value=v))
    return labels, clus.labelFingerprint

  def RemoveLabels(self, cluster_ref, remove_labels):
    raise NotImplementedError('RemoveLabels is not overriden')


class V1Adapter(APIAdapter):
  """APIAdapter for v1."""

  def CreateCluster(self, cluster_ref, options):
    cluster = self.CreateClusterCommon(cluster_ref, options)
    create_cluster_req = self.messages.CreateClusterRequest(cluster=cluster)

    req = self.messages.ContainerProjectsZonesClustersCreateRequest(
        createClusterRequest=create_cluster_req,
        projectId=cluster_ref.projectId,
        zone=cluster_ref.zone)
    operation = self.client.projects_zones_clusters.Create(req)
    return self.ParseOperation(operation.name, cluster_ref.zone)

  def UpdateCluster(self, cluster_ref, options):
    update = self.UpdateClusterCommon(options)
    op = self.client.projects_zones_clusters.Update(
        self.messages.ContainerProjectsZonesClustersUpdateRequest(
            clusterId=cluster_ref.clusterId,
            zone=cluster_ref.zone,
            projectId=cluster_ref.projectId,
            updateClusterRequest=self.messages.UpdateClusterRequest(
                update=update)))
    return self.ParseOperation(op.name, cluster_ref.zone)

  def SetNetworkPolicy(self, cluster_ref, options):
    netpol = self.SetNetworkPolicyCommon(options)
    request = self.messages.SetNetworkPolicyRequest(networkPolicy=netpol)
    req = self.messages.ContainerProjectsZonesClustersSetNetworkPolicyRequest(
        clusterId=cluster_ref.clusterId,
        zone=cluster_ref.zone,
        projectId=cluster_ref.projectId,
        setNetworkPolicyRequest=request)
    return self.ParseOperation(
        self.client.projects_zones_clusters.SetNetworkPolicy(req).name,
        cluster_ref.zone)

  def SetLegacyAuthorization(self, cluster_ref, enable_legacy_authorization):
    op = self.client.projects_zones_clusters.LegacyAbac(
        self.messages.ContainerProjectsZonesClustersLegacyAbacRequest(
            clusterId=cluster_ref.clusterId,
            zone=cluster_ref.zone,
            projectId=cluster_ref.projectId,
            setLegacyAbacRequest=self.messages.SetLegacyAbacRequest(
                enabled=bool(enable_legacy_authorization))))
    return self.ParseOperation(op.name, cluster_ref.zone)

  def SetMasterAuth(self, cluster_ref, options):
    update, action = self.SetMasterAuthCommon(options)
    request = self.messages.SetMasterAuthRequest(
        action=action,
        update=update)
    req = self.messages.ContainerProjectsZonesClustersSetMasterAuthRequest(
        clusterId=cluster_ref.clusterId,
        zone=cluster_ref.zone,
        projectId=cluster_ref.projectId,
        setMasterAuthRequest=request)
    op = self.client.projects_zones_clusters.SetMasterAuth(req)
    return self.ParseOperation(op.name, cluster_ref.zone)

  def StartIpRotation(self, cluster_ref):
    operation = self.client.projects_zones_clusters.StartIpRotation(
        self.messages.ContainerProjectsZonesClustersStartIpRotationRequest(
            clusterId=cluster_ref.clusterId,
            zone=cluster_ref.zone,
            projectId=cluster_ref.projectId))
    return self.ParseOperation(operation.name, cluster_ref.zone)

  def CompleteIpRotation(self, cluster_ref):
    operation = self.client.projects_zones_clusters.CompleteIpRotation(
        self.messages.ContainerProjectsZonesClustersCompleteIpRotationRequest(
            clusterId=cluster_ref.clusterId,
            zone=cluster_ref.zone,
            projectId=cluster_ref.projectId))
    return self.ParseOperation(operation.name, cluster_ref.zone)

  def CreateNodePool(self, node_pool_ref, options):
    pool = self.CreateNodePoolCommon(node_pool_ref, options)
    create_node_pool_req = self.messages.CreateNodePoolRequest(nodePool=pool)

    req = self.messages.ContainerProjectsZonesClustersNodePoolsCreateRequest(
        projectId=node_pool_ref.projectId,
        zone=node_pool_ref.zone,
        clusterId=node_pool_ref.clusterId,
        createNodePoolRequest=create_node_pool_req)
    operation = self.client.projects_zones_clusters_nodePools.Create(req)
    return self.ParseOperation(operation.name, node_pool_ref.zone)

  def UpdateNodePool(self, node_pool_ref, options):
    node_management = self.UpdateNodePoolCommon(node_pool_ref, options)
    req = (self.messages.
           ContainerProjectsZonesClustersNodePoolsSetManagementRequest(
               projectId=node_pool_ref.projectId,
               zone=node_pool_ref.zone,
               clusterId=node_pool_ref.clusterId,
               nodePoolId=node_pool_ref.nodePoolId,
               setNodePoolManagementRequest=
               self.messages.SetNodePoolManagementRequest(
                   management=node_management)))
    operation = self.client.projects_zones_clusters_nodePools.SetManagement(req)
    return self.ParseOperation(operation.name, node_pool_ref.zone)

  def RollbackUpgrade(self, node_pool_ref):
    operation = self.client.projects_zones_clusters_nodePools.Rollback(
        self.messages.ContainerProjectsZonesClustersNodePoolsRollbackRequest(
            clusterId=node_pool_ref.clusterId,
            zone=node_pool_ref.zone,
            projectId=node_pool_ref.projectId,
            nodePoolId=node_pool_ref.nodePoolId))
    return self.ParseOperation(operation.name, node_pool_ref.zone)

  def CancelOperation(self, op_ref):
    req = self.messages.ContainerProjectsZonesOperationsCancelRequest(
        zone=op_ref.zone,
        projectId=op_ref.projectId,
        operationId=op_ref.operationId)
    return self.client.projects_zones_operations.Cancel(req)

  def UpdateLabels(self, cluster_ref, update_labels):
    labels, fingerprint = self.UpdateLabelsCommon(
        cluster_ref, update_labels)
    req = self.messages.SetLabelsRequest(
        resourceLabels=labels, labelFingerprint=fingerprint)
    operation = self.client.projects_zones_clusters.ResourceLabels(
        self.messages.ContainerProjectsZonesClustersResourceLabelsRequest(
            clusterId=cluster_ref.clusterId,
            zone=cluster_ref.zone,
            projectId=cluster_ref.projectId,
            setLabelsRequest=req))
    return self.ParseOperation(operation.name, cluster_ref.zone)

  def RemoveLabels(self, cluster_ref, remove_labels):
    labels, fingerprint = self.RemoveLabelsCommon(
        cluster_ref, remove_labels)
    req = self.messages.SetLabelsRequest(
        resourceLabels=labels, labelFingerprint=fingerprint)

    operation = self.client.projects_zones_clusters.ResourceLabels(
        self.messages.ContainerProjectsZonesClustersResourceLabelsRequest(
            clusterId=cluster_ref.clusterId,
            zone=cluster_ref.zone,
            projectId=cluster_ref.projectId,
            setLabelsRequest=req))
    return self.ParseOperation(operation.name, cluster_ref.zone)


class V1Alpha1Adapter(APIAdapter):
  """APIAdapter for v1alpha1."""

  def CreateCluster(self, cluster_ref, options):
    cluster = self.CreateClusterCommon(cluster_ref, options)
    req = self.messages.CreateClusterRequest(
        cluster=cluster,
        projectId=cluster_ref.projectId,
        zone=cluster_ref.zone)
    operation = self.client.projects_zones_clusters.Create(req)
    return self.ParseOperation(operation.name, cluster_ref.zone)

  def UpdateCluster(self, cluster_ref, options):
    update = self.UpdateClusterCommon(options)
    op = self.client.projects_zones_clusters.Update(
        self.messages.UpdateClusterRequest(
            clusterId=cluster_ref.clusterId,
            zone=cluster_ref.zone,
            projectId=cluster_ref.projectId,
            update=update))
    return self.ParseOperation(op.name, cluster_ref.zone)

  def SetNetworkPolicy(self, cluster_ref, options):
    netpol = self.SetNetworkPolicyCommon(options)
    req = self.messages.SetNetworkPolicyRequest(
        clusterId=cluster_ref.clusterId,
        zone=cluster_ref.zone,
        projectId=cluster_ref.projectId,
        networkPolicy=netpol)
    return self.ParseOperation(
        self.client.projects_zones_clusters.SetNetworkPolicy(req).name,
        cluster_ref.zone)

  def SetLegacyAuthorization(self, cluster_ref, enable_legacy_authorization):
    op = self.client.projects_zones_clusters.LegacyAbac(
        self.messages.SetLegacyAbacRequest(
            clusterId=cluster_ref.clusterId,
            zone=cluster_ref.zone,
            projectId=cluster_ref.projectId,
            enabled=bool(enable_legacy_authorization)))
    return self.ParseOperation(op.name, cluster_ref.zone)

  def SetMasterAuth(self, cluster_ref, options):
    update, action = self.SetMasterAuthCommon(options)
    req = self.messages.SetMasterAuthRequest(
        clusterId=cluster_ref.clusterId,
        zone=cluster_ref.zone,
        projectId=cluster_ref.projectId,
        action=action,
        update=update)
    op = self.client.projects_zones_clusters.SetMasterAuth(req)
    return self.ParseOperation(op.name, cluster_ref.zone)

  def StartIpRotation(self, cluster_ref):
    operation = self.client.projects_zones_clusters.StartIpRotation(
        self.messages.StartIPRotationRequest(
            clusterId=cluster_ref.clusterId,
            zone=cluster_ref.zone,
            projectId=cluster_ref.projectId))
    return self.ParseOperation(operation.name, cluster_ref.zone)

  def CompleteIpRotation(self, cluster_ref):
    operation = self.client.projects_zones_clusters.CompleteIpRotation(
        self.messages.CompleteIPRotationRequest(
            clusterId=cluster_ref.clusterId,
            zone=cluster_ref.zone,
            projectId=cluster_ref.projectId))
    return self.ParseOperation(operation.name, cluster_ref.zone)

  def CreateNodePool(self, node_pool_ref, options):
    pool = self.CreateNodePoolCommon(node_pool_ref, options)
    req = self.messages.CreateNodePoolRequest(
        nodePool=pool,
        projectId=node_pool_ref.projectId,
        zone=node_pool_ref.zone,
        clusterId=node_pool_ref.clusterId)
    operation = self.client.projects_zones_clusters_nodePools.Create(req)
    return self.ParseOperation(operation.name, node_pool_ref.zone)

  def UpdateNodePool(self, node_pool_ref, options):
    node_management = self.UpdateNodePoolCommon(node_pool_ref, options)
    req = (self.messages.SetNodePoolManagementRequest(
        projectId=node_pool_ref.projectId,
        zone=node_pool_ref.zone,
        clusterId=node_pool_ref.clusterId,
        nodePoolId=node_pool_ref.nodePoolId,
        management=node_management))
    operation = self.client.projects_zones_clusters_nodePools.SetManagement(req)
    return self.ParseOperation(operation.name, node_pool_ref.zone)

  def RollbackUpgrade(self, node_pool_ref):
    operation = self.client.projects_zones_clusters_nodePools.Rollback(
        self.messages.RollbackNodePoolUpgradeRequest(
            clusterId=node_pool_ref.clusterId,
            zone=node_pool_ref.zone,
            projectId=node_pool_ref.projectId,
            nodePoolId=node_pool_ref.nodePoolId))
    return self.ParseOperation(operation.name, node_pool_ref.zone)

  def CancelOperation(self, op_ref):
    req = self.messages.CancelOperationRequest(
        zone=op_ref.zone,
        projectId=op_ref.projectId,
        operationId=op_ref.operationId)
    return self.client.projects_zones_operations.Cancel(req)

  def UpdateLabels(self, cluster_ref, update_labels):
    labels, fingerprint = self.UpdateLabelsCommon(
        cluster_ref, update_labels)
    operation = self.client.projects_zones_clusters.ResourceLabels(
        self.messages.SetLabelsRequest(
            clusterId=cluster_ref.clusterId,
            zone=cluster_ref.zone,
            projectId=cluster_ref.projectId,
            resourceLabels=labels,
            labelFingerprint=fingerprint))
    return self.ParseOperation(operation.name, cluster_ref.zone)

  def RemoveLabels(self, cluster_ref, remove_labels):
    labels, fingerprint = self.RemoveLabelsCommon(
        cluster_ref, remove_labels)
    operation = self.client.projects_zones_clusters.ResourceLabels(
        self.messages.SetLabelsRequest(
            clusterId=cluster_ref.clusterId,
            zone=cluster_ref.zone,
            projectId=cluster_ref.projectId,
            resourceLabels=labels,
            labelFingerprint=fingerprint))
    return self.ParseOperation(operation.name, cluster_ref.zone)


def _AddNodeLabelsToNodeConfig(node_config, options):
  if options.node_labels is None:
    return
  labels = node_config.LabelsValue()
  props = []
  for key, value in options.node_labels.iteritems():
    props.append(labels.AdditionalProperty(key=key, value=value))
  labels.additionalProperties = props
  node_config.labels = labels
