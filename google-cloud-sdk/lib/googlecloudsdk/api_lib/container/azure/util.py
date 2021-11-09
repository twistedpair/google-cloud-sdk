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

"""Utilities Cloud GKE Multi-cloud for Azure API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import exceptions as apitools_exceptions
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.container.gkemulticloud import util
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log


class _AzureClientBase(object):
  """Base class for Azure clients."""

  def __init__(self, client=None, messages=None, track=base.ReleaseTrack.GA):
    self.track = track
    self.client = client or util.GetClientInstance(track)
    self.messages = messages or util.GetMessagesModule(track)
    self._service = self._GetService()

  def List(self, parent_ref, page_size, limit):
    """List Azure resources."""

    req = self._service.GetRequestType('List')(parent=parent_ref.RelativeName())

    try:
      for item in list_pager.YieldFromList(
          self._service,
          req,
          field=self.GetListResultsField(),
          limit=limit,
          batch_size=page_size,
          batch_size_attribute='pageSize'):
        yield item
    # TODO(b/203617640): Remove handling of this exception once API has gone GA.
    except apitools_exceptions.HttpNotFoundError as e:
      if 'Method not found' in e.content:
        log.warning(
            'This project may not have been added to the allow list for the Anthos Multi-Cloud API, please reach out to your GCP account team to resolve this'
        )
      raise

  def Get(self, resource_ref):
    """Get an Azure resource."""

    req = self._service.GetRequestType('Get')(name=resource_ref.RelativeName())
    return self._service.Get(req)

  def Delete(self, resource_ref, validate_only=None, allow_missing=None):
    """Delete an Azure resource."""

    req = self._service.GetRequestType('Delete')(
        name=resource_ref.RelativeName())
    if validate_only:
      req.validateOnly = True
    if allow_missing:
      req.allowMissing = True

    return self._service.Delete(req)

  def _GetService(self):
    raise NotImplementedError(
        '_GetService() method not implemented for this type')

  def GetListResultsField(self):
    raise NotImplementedError(
        'GetListResultsField() method not implemented for this type')

  def _CreateAzureDiskTemplate(self, size_gib):
    # Using this to hide the 'v1alpha' that shows up in the type.
    version = util.GetApiVersionForTrack(self.track).capitalize()
    msg = 'GoogleCloudGkemulticloud{}AzureDiskTemplate'.format(version)
    return getattr(self.messages, msg)(sizeGib=size_gib)

  def _CreateProxyConfig(self, **kwargs):
    # Using this to hide the 'v1alpha' that shows up in the type.
    version = util.GetApiVersionForTrack(self.track).capitalize()
    msg = 'GoogleCloudGkemulticloud{}AzureProxyConfig'.format(version)
    return getattr(self.messages, msg)(**kwargs)

  def _CreateConfigEncryption(self, **kwargs):
    version = util.GetApiVersionForTrack(self.track).capitalize()
    msg = 'GoogleCloudGkemulticloud{}AzureConfigEncryption'.format(version)
    return getattr(self.messages, msg)(**kwargs)


class ClustersClient(_AzureClientBase):
  """Client for Azure Clusters in the gkemulticloud API."""

  def Create(self,
             cluster_ref,
             client_ref=None,
             azure_region=None,
             resource_group_id=None,
             vnet_id=None,
             pod_address_cidr_blocks=None,
             service_address_cidr_blocks=None,
             cluster_version=None,
             subnet_id=None,
             vm_size=None,
             ssh_public_key=None,
             proxy_resource_group_id=None,
             proxy_secret_id=None,
             main_volume_size=None,
             root_volume_size=None,
             validate_only=False,
             tags=None,
             admin_users=None,
             replica_placements=None,
             fleet_project=None,
             service_load_balancer_subnet_id=None,
             endpoint_subnet_id=None,
             database_encryption_key_id=None,
             config_encryption_key_id=None,
             config_encryption_public_key=None):
    """Create a new Azure Cluster."""
    req = self._service.GetRequestType('Create')(
        azureClusterId=cluster_ref.azureClustersId,
        parent=cluster_ref.Parent().RelativeName())
    if validate_only:
      req.validateOnly = True

    c = self._AddAzureCluster(req)
    c.name = cluster_ref.azureClustersId
    c.azureClient = client_ref.RelativeName()
    c.azureRegion = azure_region
    c.resourceGroupId = resource_group_id
    c.authorization = self._CreateAuthorization(admin_users)

    net = self._AddAzureNetworking(c)
    net.podAddressCidrBlocks.append(pod_address_cidr_blocks)
    net.serviceAddressCidrBlocks.append(service_address_cidr_blocks)
    net.virtualNetworkId = vnet_id
    if service_load_balancer_subnet_id is not None:
      net.serviceLoadBalancerSubnetId = service_load_balancer_subnet_id

    cp = self._AddAzureControlPlane(c)

    if main_volume_size:
      cp.mainVolume = self._CreateAzureDiskTemplate(main_volume_size)
    if root_volume_size:
      cp.rootVolume = self._CreateAzureDiskTemplate(root_volume_size)

    cp.sshConfig = self._CreateSshConfig(authorizedKey=ssh_public_key)
    cp.subnetId = subnet_id
    cp.version = cluster_version
    cp.vmSize = vm_size

    if proxy_resource_group_id is not None and proxy_secret_id is not None:
      cp.proxyConfig = self._CreateProxyConfig(
          resourceGroupId=proxy_resource_group_id, secretId=proxy_secret_id)

    if replica_placements:
      cp.replicaPlacements.extend(replica_placements)

    if endpoint_subnet_id is not None:
      cp.endpointSubnetId = endpoint_subnet_id

    if database_encryption_key_id is not None:
      cp.databaseEncryption = self._CreateDatabaseEncryption(
          keyId=database_encryption_key_id)

    if config_encryption_key_id is not None:
      cp.configEncryption = self._CreateConfigEncryption(
          keyId=config_encryption_key_id,
          publicKey=config_encryption_public_key)

    if tags:
      tag_type = type(cp).TagsValue.AdditionalProperty
      cp.tags = type(cp).TagsValue(additionalProperties=[
          tag_type(key=k, value=v) for k, v in tags.items()
      ])

    if fleet_project:
      c.fleet = self._CreateFleet(fleet_project)

    return self._service.Create(req)

  def GenerateAccessToken(self, cluster_ref):
    """Generates an access token for an Azure cluster."""
    req = self._service.GetRequestType('GenerateAzureAccessToken')(
        azureCluster=cluster_ref.RelativeName())
    return self._service.GenerateAzureAccessToken(req)

  def GetKubeConfig(self, cluster_ref):
    req = self._service.GetRequestType('GetAzureClusterAdminKubeconfig')(
        azureCluster=cluster_ref.RelativeName())
    return self._service.GetAzureClusterAdminKubeconfig(req)

  def GetListResultsField(self):
    return 'azureClusters'

  def Update(self,
             cluster_ref,
             client_ref=None,
             cluster_version=None,
             validate_only=False):
    """Updates an Anthos cluster on Azure.

    Args:
      cluster_ref: obj, Cluster object to be updated.
      client_ref: obj, Client to use in the cluster update.
      cluster_version: str, Cluster version to use in the cluster update.
      validate_only: bool, Validate the update of the cluster.

    Returns:
      Response to the update request.
    """
    req = self._service.GetRequestType('Patch')(
        name=cluster_ref.RelativeName(),)
    if validate_only:
      req.validateOnly = True

    update_mask = []

    c = self._AddAzureCluster(req)
    if client_ref:
      c.azureClient = client_ref.RelativeName()
      update_mask.append('azure_client')

    cp = self._AddAzureControlPlane(c)
    if cluster_version:
      cp.version = cluster_version
      update_mask.append('control_plane.version')

    req.updateMask = ','.join(update_mask)

    return self._service.Patch(req)

  def _GetService(self):
    return self.client.projects_locations_azureClusters

  def _AddAzureCluster(self, req):
    # Using this to hide the 'v1alpha' that shows up in the type.
    version = util.GetApiVersionForTrack(self.track).capitalize()
    msg = 'GoogleCloudGkemulticloud{}AzureCluster'.format(version)
    attr = 'googleCloudGkemulticloud{}AzureCluster'.format(version)
    cluster = getattr(self.messages, msg)()
    setattr(req, attr, cluster)
    return cluster

  def _AddAzureNetworking(self, req):
    # Using this to hide the 'v1alpha' that shows up in the type.
    version = util.GetApiVersionForTrack(self.track).capitalize()
    msg = 'GoogleCloudGkemulticloud{}AzureClusterNetworking'.format(version)
    net = getattr(self.messages, msg)()
    req.networking = net
    return net

  def _AddAzureControlPlane(self, req):
    # Using this to hide the 'v1alpha' that shows up in the type.
    version = util.GetApiVersionForTrack(self.track).capitalize()
    msg = 'GoogleCloudGkemulticloud{}AzureControlPlane'.format(version)
    cp = getattr(self.messages, msg)()
    req.controlPlane = cp
    return cp

  def _CreateDatabaseEncryption(self, **kwargs):
    version = util.GetApiVersionForTrack(self.track).capitalize()
    msg = 'GoogleCloudGkemulticloud{}AzureDatabaseEncryption'.format(version)
    return getattr(self.messages, msg)(**kwargs)

  def _CreateFleet(self, fleet_project):
    version = util.GetApiVersionForTrack(self.track).capitalize()
    msg = 'GoogleCloudGkemulticloud{}Fleet'.format(version)
    fleet = getattr(self.messages, msg)(project=fleet_project)
    return fleet

  def _CreateSshConfig(self, **kwargs):
    # Using this to hide the 'v1alpha' that shows up in the type.
    version = util.GetApiVersionForTrack(self.track).capitalize()
    msg = 'GoogleCloudGkemulticloud{}AzureSshConfig'.format(version)
    return getattr(self.messages, msg)(**kwargs)

  def _CreateAuthorization(self, admin_users):
    """Create an Azure Authorization message.

    Args:
      admin_users: list of strings, admin users.

    Returns:
      A GoogleCloudGkemulticloudAzureAuthorization message.
    """
    # Using this to hide the 'v1alpha' that shows up in the type.
    version = util.GetApiVersionForTrack(self.track).capitalize()

    cluster_user_msg = 'GoogleCloudGkemulticloud{}AzureClusterUser'.format(
        version)

    users = []
    if admin_users:
      users = [
          getattr(self.messages, cluster_user_msg)(username=u)
          for u in admin_users
      ]

    msg = 'GoogleCloudGkemulticloud{}AzureAuthorization'.format(version)
    return getattr(self.messages, msg)(adminUsers=users)


class NodePoolsClient(_AzureClientBase):
  """Client for Azure Node Pools in the gkemulticloud API."""

  def __init__(self, **kwargs):
    self._message_prefix = 'GoogleCloudGkemulticloud'
    self.__attribute_prefix = 'googleCloudGkemulticloud'
    super(NodePoolsClient, self).__init__(**kwargs)

  def __AddMessageForTrack(self, req, type_name, **kwargs):
    """For adding messages where attribute and type have a very long name."""
    version = util.GetApiVersionForTrack(self.track).capitalize()
    msg = '{}{}{}'.format(self._message_prefix, version, type_name)
    attr = '{}{}{}'.format(self.__attribute_prefix, version, type_name)
    instance = getattr(self.messages, msg)(**kwargs)
    setattr(req, attr, instance)
    return instance

  def Create(self,
             nodepool_ref,
             node_version=None,
             subnet_id=None,
             vm_size=None,
             ssh_public_key=None,
             proxy_resource_group_id=None,
             proxy_secret_id=None,
             root_volume_size=None,
             tags=None,
             validate_only=None,
             min_nodes=None,
             max_nodes=None,
             max_pods_per_node=None,
             taints=None,
             labels=None,
             azure_availability_zone=None,
             config_encryption_key_id=None,
             config_encryption_public_key=None):
    """Create a new Azure Node Pool."""
    req = self._service.GetRequestType('Create')(
        azureNodePoolId=nodepool_ref.azureNodePoolsId,
        parent=nodepool_ref.Parent().RelativeName(),
        validateOnly=validate_only)

    nodepool = self.__AddMessageForTrack(
        req,
        'AzureNodePool',
        name=nodepool_ref.azureNodePoolsId,
        subnetId=subnet_id,
        version=node_version)
    nodepool.azureAvailabilityZone = azure_availability_zone

    nodepool.autoscaling = type(nodepool).autoscaling.type(
        maxNodeCount=max_nodes, minNodeCount=min_nodes)

    nodepool.maxPodsConstraint = type(nodepool).maxPodsConstraint.type(
        maxPodsPerNode=max_pods_per_node)

    nodepool.config = type(nodepool).config.type(vmSize=vm_size)

    nodeconfig = nodepool.config
    nodeconfig.sshConfig = type(nodeconfig).sshConfig.type(
        authorizedKey=ssh_public_key)
    nodeconfig.taints.extend(taints)

    if config_encryption_key_id is not None:
      nodeconfig.configEncryption = self._CreateConfigEncryption(
          keyId=config_encryption_key_id,
          publicKey=config_encryption_public_key)

    if proxy_resource_group_id is not None and proxy_secret_id is not None:
      nodeconfig.proxyConfig = self._CreateProxyConfig(
          resourceGroupId=proxy_resource_group_id, secretId=proxy_secret_id)

    if root_volume_size:
      nodeconfig.rootVolume = self._CreateAzureDiskTemplate(root_volume_size)

    if tags:
      tag_type = type(nodeconfig).TagsValue.AdditionalProperty
      nodeconfig.tags = type(nodeconfig).TagsValue(additionalProperties=[
          tag_type(key=k, value=v) for k, v in tags.items()
      ])

    if labels:
      label_type = type(nodeconfig).LabelsValue.AdditionalProperty
      nodeconfig.labels = type(nodeconfig).LabelsValue(additionalProperties=[
          label_type(key=k, value=v) for k, v in labels.items()
      ])

    return self._service.Create(req)

  def Update(self,
             nodepool_ref,
             node_version=None,
             min_nodes=None,
             max_nodes=None,
             validate_only=None):
    """Updates a node pool in an Anthos cluster on Azure including node pool version.

    Args:
      nodepool_ref: obj, Node pool object to be updated.
      node_version: str, Node pool version to use in the node pool update.
      min_nodes: int, Minimum number of nodes in the node pool.
      max_nodes: int, Maximum number of nodes in the node pool.
      validate_only: bool, Validate the update of the node pool.

    Returns:
      Response to the update request.
    """
    req = self._service.GetRequestType('Patch')(
        name=nodepool_ref.RelativeName(),
        validateOnly=validate_only)

    update_mask = []

    nodepool = self.__AddMessageForTrack(
        req, 'AzureNodePool', name=nodepool_ref.azureNodePoolsId)

    if node_version:
      nodepool.version = node_version
      update_mask.append('version')

    nodepool.autoscaling = type(nodepool).autoscaling.type()
    if min_nodes is not None:
      nodepool.autoscaling.minNodeCount = min_nodes
      update_mask.append('autoscaling.minNodeCount')
    if max_nodes is not None:
      nodepool.autoscaling.maxNodeCount = max_nodes
      update_mask.append('autoscaling.maxNodeCount')

    req.updateMask = ','.join(update_mask)
    return self._service.Patch(req)

  def _GetService(self):
    return self.client.projects_locations_azureClusters_azureNodePools

  def GetListResultsField(self):
    return 'azureNodePools'


class ClientsClient(_AzureClientBase):
  """Client for Azure Clients in the gkemulticloud API."""

  def Create(self, client_ref, tenant_id, application_id, validate_only=False):
    """Create a new Azure client."""
    req = self.messages.GkemulticloudProjectsLocationsAzureClientsCreateRequest(
        azureClientId=client_ref.azureClientsId,
        parent=client_ref.Parent().RelativeName())
    if validate_only:
      req.validateOnly = True

    client = self._AddClient(req)
    client.name = client_ref.azureClientsId
    client.applicationId = application_id
    client.tenantId = tenant_id

    return self._service.Create(req)

  def GetListResultsField(self):
    return 'azureClients'

  def _GetService(self):
    return self.client.projects_locations_azureClients

  def _AddClient(self, req):
    # Using this to hide the 'v1alpha' that shows up in the type.
    version = util.GetApiVersionForTrack(self.track).capitalize()
    msg = 'GoogleCloudGkemulticloud{}AzureClient'.format(version)
    attr = 'googleCloudGkemulticloud{}AzureClient'.format(version)
    client = getattr(self.messages, msg)()
    setattr(req, attr, client)
    return client
