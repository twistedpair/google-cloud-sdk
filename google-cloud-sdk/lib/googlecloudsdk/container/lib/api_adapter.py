# Copyright 2015 Google Inc. All Rights Reserved.

"""Api client adapter containers commands."""
import time

from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resolvers
from googlecloudsdk.core import resources as cloud_resources
from googlecloudsdk.core.console import console_io
from googlecloudsdk.shared.compute import constants
from googlecloudsdk.third_party.apis.container import v1 as container_v1
from googlecloudsdk.third_party.apitools.base import py as apitools_base

from googlecloudsdk.container.lib import util

WRONG_ZONE_ERROR_MSG = """\
{error}
Could not find [{name}] in [{wrong_zone}].
Did you mean [{name}] in [{zone}]?"""
NO_SUCH_CLUSTER_ERROR_MSG = """\
{error}
No cluster named '{name}' in {project}."""


def NewAPIAdapter(api_version, endpoint_url, http):
  """Initialize an api adapter for the given api_version.

  Args:
    api_version: str, version to create api adapter for.
    endpoint_url: str, endpoint url for the api client.
    http: httplib2.Http object for api client to use.

  Returns:
    APIAdapter object.
  """
  if api_version == 'v1':
    api = container_v1
    api_client = api.ContainerV1
    zone_field = 'zone'
    adapter = V1Adapter
  else:
    raise exceptions.InvalidArgumentException(
        'api_client_overrides/container',
        '{0} is not a valid api version'.format(api_version))

  api_client = api_client(url=endpoint_url, get_credentials=False, http=http)
  messages = api
  registry = cloud_resources.REGISTRY.CloneAndSwitchAPIs(api_client)
  registry.SetParamDefault(
      api='compute', collection=None, param='project',
      resolver=resolvers.FromProperty(properties.VALUES.core.project))
  registry.SetParamDefault(
      api='container', collection=None, param='projectId',
      resolver=resolvers.FromProperty(properties.VALUES.core.project))
  registry.SetParamDefault(
      api='container', collection=None, param=zone_field,
      resolver=resolvers.FromProperty(properties.VALUES.compute.zone))

  return adapter(api_version, registry, api_client, messages)


_REQUIRED_SCOPES = [
    constants.SCOPES['compute-rw'],
    constants.SCOPES['storage-ro'],
]


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
    expanded = constants.SCOPES.get(scope, None)
    if not expanded:
      # Assume the scope exists but is not public. Backend does the actual
      # lookup to see what scopes the project can use and will kick back
      # an error if a requested scope not allowed
      expanded = scope
    scope_uris.append(expanded)
  return scope_uris


class APIAdapter(object):
  """Handles making api requests in a version-agnostic way."""

  def __init__(self, api_version, registry, client, messages):
    self.api_version = api_version
    self.registry = registry
    self.client = client
    self.messages = messages

  def ParseCluster(self, name):
    properties.VALUES.compute.zone.Get(required=True)
    properties.VALUES.core.project.Get(required=True)
    return self.registry.Parse(
        name, collection='container.projects.zones.clusters')

  def Zone(self, cluster_ref):
    raise NotImplementedError('Zone is not overriden')

  def Version(self, cluster):
    raise NotImplementedError('Version is not overriden')

  def PrintClusters(self, clusters):
    raise NotImplementedError('PrintClusters is not overriden')

  def PrintOperations(self, operations):
    raise NotImplementedError('PrintOperations is not overriden')

  def ParseOperation(self, operation_id):
    properties.VALUES.compute.zone.Get(required=True)
    properties.VALUES.core.project.Get(required=True)
    return self.registry.Parse(
        operation_id, collection='container.projects.zones.operations')

  def CreateCluster(self, cluster_ref, **options):
    raise NotImplementedError('CreateCluster is not overriden')

  def DeleteCluster(self, cluster_ref):
    raise NotImplementedError('DeleteCluster is not overriden')

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
      return self.client.projects_zones_clusters.Get(cluster_ref.Request())
    except apitools_base.HttpError as error:
      api_error = util.GetError(error)
      if api_error.code != 404:
        raise api_error

    # Cluster couldn't be found, maybe user got zone wrong?
    try:
      clusters = self.ListClusters(cluster_ref.projectId).clusters
    except apitools_base.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))
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

  def ListClusters(self, project, zone=None):
    raise NotImplementedError('ListClusters is not overriden')

  def UpdateCluster(self, cluster_ref, options):
    raise NotImplementedError('Update requires a v1 client.')

  def GetOperation(self, operation_ref):
    return self.client.projects_zones_operations.Get(
        operation_ref.Request())

  def GetOperationError(self, operation_ref):
    raise NotImplementedError('GetOperationError is not overriden')

  def IsOperationFinished(self, operation):
    raise NotImplementedError('IsOperationFinished is not overriden')

  def IsRunning(self, cluster):
    raise NotImplementedError('IsRunning is not overriden')

  def ListOperations(self, project, zone=None):
    raise NotImplementedError('ListOperations is not overriden')

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
    with console_io.ProgressTracker(message, autotick=True):
      start_time = time.clock()
      while timeout_s > (time.clock() - start_time):
        try:
          operation = self.GetOperation(operation_ref)
          if self.IsOperationFinished(operation):
            # Success!
            log.info('Operation %s succeeded after %.3f seconds',
                     operation, (time.clock() - start_time))
            break
        except apitools_base.HttpError as error:
          log.debug('GetOperation failed: %s', error)
          # Keep trying until we timeout in case error is transient.
        time.sleep(poll_period_s)
    if not self.IsOperationFinished(operation):
      log.err.Print('Timed out waiting for operation {0}'.format(operation))
      raise util.Error(
          'Operation [{0}] is still running'.format(operation))
    if self.GetOperationError(operation):
      raise util.Error('Operation [{0}] finished with error: {1}'.format(
          operation, self.GetOperationError(operation)))

    return operation

  def GetServerConfig(self, project, zone):
    raise NotImplementedError('GetServerConfig is not overriden')


class CreateClusterOptions(object):

  def __init__(self,
               node_machine_type=None,
               node_source_image=None,
               node_disk_size_gb=None,
               scopes=None,
               num_nodes=None,
               user=None,
               password=None,
               cluster_version=None,
               network=None,
               cluster_ipv4_cidr=None,
               enable_cloud_logging=None,
               enable_cloud_monitoring=None):
    self.node_machine_type = node_machine_type
    self.node_source_image = node_source_image
    self.node_disk_size_gb = node_disk_size_gb
    self.scopes = scopes
    self.num_nodes = num_nodes
    self.user = user
    self.password = password
    self.cluster_version = cluster_version
    self.network = network
    self.cluster_ipv4_cidr = cluster_ipv4_cidr
    self.enable_cloud_logging = enable_cloud_logging
    self.enable_cloud_monitoring = enable_cloud_monitoring


class UpdateClusterOptions(object):

  def __init__(self,
               version=None,
               update_master=None,
               update_nodes=None,
               update_cluster=None,
               monitoring_service=None):
    self.version = version
    self.update_master = bool(update_master)
    self.update_nodes = bool(update_nodes)
    self.update_cluster = bool(update_cluster)
    self.monitoring_service = str(monitoring_service)


class V1Adapter(APIAdapter):
  """APIAdapter for v1."""

  def Zone(self, cluster_ref):
    return cluster_ref.zone

  def Version(self, cluster):
    return cluster.currentMasterVersion

  def PrintClusters(self, clusters):
    list_printer.PrintResourceList(
        'container.projects.zones.clusters', clusters)

  def PrintOperations(self, operations):
    list_printer.PrintResourceList(
        'container.projects.zones.operations', operations)

  def CreateCluster(self, cluster_ref, options):
    node_config = self.messages.NodeConfig()
    if options.node_machine_type:
      node_config.machineType = options.node_machine_type
    # TODO(user): support disk size via flag
    if options.node_disk_size_gb:
      node_config.diskSizeGb = options.node_disk_size_gb
    if options.node_source_image:
      raise util.Error('cannot specify node source image in container v1 api')
    scope_uris = ExpandScopeURIs(options.scopes)
    node_config.oauthScopes = sorted(set(scope_uris + _REQUIRED_SCOPES))

    cluster = self.messages.Cluster(
        name=cluster_ref.clusterId,
        initialNodeCount=options.num_nodes,
        nodeConfig=node_config,
        masterAuth=self.messages.MasterAuth(username=options.user,
                                            password=options.password))
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

    create_cluster_req = self.messages.CreateClusterRequest(cluster=cluster)

    req = self.messages.ContainerProjectsZonesClustersCreateRequest(
        createClusterRequest=create_cluster_req,
        projectId=cluster_ref.projectId,
        zone=cluster_ref.zone)
    operation = self.client.projects_zones_clusters.Create(req)
    return self.ParseOperation(operation.name)

  def UpdateCluster(self, cluster_ref, options):
    if not options.version:
      options.version = '-'
    if options.update_nodes:
      update = self.messages.ClusterUpdate(
          desiredNodeVersion=options.version)
    elif options.update_master:
      update = self.messages.ClusterUpdate(
          desiredMasterVersion=options.version)
    elif options.update_cluster:
      update = self.messages.ClusterUpdate(
          desiredMonitoringService=options.monitoring_service)

    op = self.client.projects_zones_clusters.Update(
        self.messages.ContainerProjectsZonesClustersUpdateRequest(
            clusterId=cluster_ref.clusterId,
            zone=cluster_ref.zone,
            projectId=cluster_ref.projectId,
            updateClusterRequest=self.messages.UpdateClusterRequest(
                update=update)))
    return self.ParseOperation(op.name)

  def DeleteCluster(self, cluster_ref):
    operation = self.client.projects_zones_clusters.Delete(
        self.messages.ContainerProjectsZonesClustersDeleteRequest(
            clusterId=cluster_ref.clusterId,
            zone=cluster_ref.zone,
            projectId=cluster_ref.projectId))
    return self.ParseOperation(operation.name)

  def ListClusters(self, project, zone=None):
    if not zone:
      zone = '-'
    req = self.messages.ContainerProjectsZonesClustersListRequest(
        projectId=project, zone=zone)
    return self.client.projects_zones_clusters.List(req)

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
