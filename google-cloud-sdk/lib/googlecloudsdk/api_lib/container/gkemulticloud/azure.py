# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Utilities for gkemulticloud API specific to Azure."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.container.gkemulticloud import update_mask
from googlecloudsdk.api_lib.container.gkemulticloud import util
from googlecloudsdk.command_lib.container.azure import resource_args


class _AzureClientBase(util.ClientBase):
  """Base class for Azure gkemulticloud API clients."""

  def _DiskTemplate(self, **kwargs):
    return self._messages.GoogleCloudGkemulticloudV1AzureDiskTemplate(
        **kwargs) if any(kwargs.values()) else None

  def _ProxyConfig(self, **kwargs):
    return self._messages.GoogleCloudGkemulticloudV1AzureProxyConfig(
        **kwargs) if any(kwargs.values()) else None

  def _ConfigEncryption(self, **kwargs):
    return self._messages.GoogleCloudGkemulticloudV1AzureConfigEncryption(
        **kwargs) if any(kwargs.values()) else None

  def _Cluster(self, **kwargs):
    return self._messages.GoogleCloudGkemulticloudV1AzureCluster(**kwargs)

  def _Client(self, **kwargs):
    return self._messages.GoogleCloudGkemulticloudV1AzureClient(**kwargs)

  def _NodePool(self, **kwargs):
    return self._messages.GoogleCloudGkemulticloudV1AzureNodePool(**kwargs)

  def _Authorization(self, admin_users):
    if admin_users is None:
      return None
    return self._messages.GoogleCloudGkemulticloudV1AzureAuthorization(
        adminUsers=[
            self._messages.GoogleCloudGkemulticloudV1AzureClusterUser(
                username=u) for u in admin_users
        ])

  def _Networking(self, **kwargs):
    return self._messages.GoogleCloudGkemulticloudV1AzureClusterNetworking(
        **kwargs) if any(kwargs.values()) else None

  def _ControlPlane(self, **kwargs):
    return self._messages.GoogleCloudGkemulticloudV1AzureControlPlane(**kwargs)

  def _SshConfig(self, **kwargs):
    return self._messages.GoogleCloudGkemulticloudV1AzureSshConfig(
        **kwargs) if any(kwargs.values()) else None

  def _DatabaseEncryption(self, **kwargs):
    return self._messages.GoogleCloudGkemulticloudV1AzureDatabaseEncryption(
        **kwargs) if any(kwargs.values()) else None

  def _Fleet(self, **kwargs):
    return self._messages.GoogleCloudGkemulticloudV1Fleet(
        **kwargs) if any(kwargs.values()) else None

  def _Autoscaling(self, **kwargs):
    return self._messages.GoogleCloudGkemulticloudV1AzureNodePoolAutoscaling(
        **kwargs) if any(kwargs.values()) else None


class ClustersClient(_AzureClientBase):
  """Client for Azure Clusters in the gkemulticloud API."""

  def __init__(self, **kwargs):
    super(ClustersClient, self).__init__(**kwargs)
    self._service = self._client.projects_locations_azureClusters
    self._list_result_field = 'azureClusters'

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
             config_encryption_public_key=None,
             logging=None):
    """Creates a new Anthos cluster on Azure."""
    cp = self._ControlPlane(
        mainVolume=self._DiskTemplate(sizeGib=main_volume_size),
        rootVolume=self._DiskTemplate(sizeGib=root_volume_size),
        sshConfig=self._SshConfig(authorizedKey=ssh_public_key),
        subnetId=subnet_id,
        version=cluster_version,
        vmSize=vm_size,
        proxyConfig=self._ProxyConfig(
            resourceGroupId=proxy_resource_group_id, secretId=proxy_secret_id),
        replicaPlacements=replica_placements if replica_placements else [],
        endpointSubnetId=endpoint_subnet_id,
        databaseEncryption=self._DatabaseEncryption(
            keyId=database_encryption_key_id),
        configEncryption=self._ConfigEncryption(
            keyId=config_encryption_key_id,
            publicKey=config_encryption_public_key))
    if tags:
      tag_type = type(cp).TagsValue.AdditionalProperty
      cp.tags = type(cp).TagsValue(additionalProperties=[
          tag_type(key=k, value=v) for k, v in tags.items()
      ])
    net = self._Networking(
        podAddressCidrBlocks=[pod_address_cidr_blocks],
        serviceAddressCidrBlocks=[service_address_cidr_blocks],
        virtualNetworkId=vnet_id,
        serviceLoadBalancerSubnetId=service_load_balancer_subnet_id)
    c = self._Cluster(
        name=cluster_ref.azureClustersId,
        azureClient=client_ref.RelativeName(),
        azureRegion=azure_region,
        resourceGroupId=resource_group_id,
        authorization=self._Authorization(admin_users),
        networking=net,
        controlPlane=cp,
        fleet=self._Fleet(project=fleet_project),
        loggingConfig=logging)
    req = self._messages.GkemulticloudProjectsLocationsAzureClustersCreateRequest(
        azureClusterId=cluster_ref.azureClustersId,
        googleCloudGkemulticloudV1AzureCluster=c,
        parent=cluster_ref.Parent().RelativeName())
    if validate_only:
      req.validateOnly = True
    return self._service.Create(req)

  def GenerateAccessToken(self, cluster_ref):
    """Generates an access token for an Azure cluster."""
    req = self._service.GetRequestType('GenerateAzureAccessToken')(
        azureCluster=cluster_ref.RelativeName())
    return self._service.GenerateAzureAccessToken(req)

  def Update(self, cluster_ref, args):
    """Updates an Anthos cluster on Azure."""
    c = self._Cluster(
        authorization=self._Authorization(args.admin_users),
        azureClient=resource_args.ParseAzureClientResourceArg(
            args).RelativeName() if args.client else None,
        controlPlane=self._ControlPlane(
            version=args.cluster_version, vmSize=args.vm_size))

    req = self._messages.GkemulticloudProjectsLocationsAzureClustersPatchRequest(
        googleCloudGkemulticloudV1AzureCluster=c,
        name=cluster_ref.RelativeName(),
        updateMask=update_mask.GetUpdateMask(
            args, update_mask.AZURE_CLUSTER_ARGS_TO_UPDATE_MASKS))
    if args.validate_only:
      req.validateOnly = True
    return self._service.Patch(req)


class NodePoolsClient(_AzureClientBase):
  """Client for Azure Node Pools in the gkemulticloud API."""

  def __init__(self, **kwargs):
    super(NodePoolsClient, self).__init__(**kwargs)
    self._service = self._client.projects_locations_azureClusters_azureNodePools
    self._list_result_field = 'azureNodePools'

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
             config_encryption_public_key=None,
             image_type=None):
    """Creates a node pool in an Anthos cluster on Azure."""
    nodepool = self._NodePool(subnetId=subnet_id, version=node_version)
    nodepool.name = nodepool_ref.azureNodePoolsId
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
      nodeconfig.configEncryption = self._ConfigEncryption(
          keyId=config_encryption_key_id,
          publicKey=config_encryption_public_key)
    if proxy_resource_group_id is not None and proxy_secret_id is not None:
      nodeconfig.proxyConfig = self._ProxyConfig(
          resourceGroupId=proxy_resource_group_id, secretId=proxy_secret_id)
    if root_volume_size:
      nodeconfig.rootVolume = self._DiskTemplate(sizeGib=root_volume_size)
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
    if image_type:
      nodeconfig.imageType = image_type

    req = self._messages.GkemulticloudProjectsLocationsAzureClustersAzureNodePoolsCreateRequest(
        azureNodePoolId=nodepool_ref.azureNodePoolsId,
        googleCloudGkemulticloudV1AzureNodePool=nodepool,
        parent=nodepool_ref.Parent().RelativeName(),
        validateOnly=validate_only)
    return self._service.Create(req)

  def Update(self, nodepool_ref, args):
    """Updates a node pool in an Anthos cluster on Azure."""
    nodepool = self._NodePool(
        name=nodepool_ref.azureNodePoolsId,
        version=args.node_version,
        autoscaling=self._Autoscaling(
            minNodeCount=args.min_nodes, maxNodeCount=args.max_nodes))

    req = self._messages.GkemulticloudProjectsLocationsAzureClustersAzureNodePoolsPatchRequest(
        googleCloudGkemulticloudV1AzureNodePool=nodepool,
        name=nodepool_ref.RelativeName(),
        updateMask=update_mask.GetUpdateMask(
            args, update_mask.AZURE_NODEPOOL_ARGS_TO_UPDATE_MASKS),
        validateOnly=args.validate_only)
    return self._service.Patch(req)

  def HasNodePools(self, cluster_ref):
    """Checks if the cluster has a node pool.

    Args:
      cluster_ref: gkemulticloud.GoogleCloudGkemulticloudV1AzureCluster object.

    Returns:
      True if the cluster has a node pool. Otherwise, False.
    """
    req = self._messages.GkemulticloudProjectsLocationsAzureClustersAzureNodePoolsListRequest(
        parent=cluster_ref.RelativeName(), pageSize=1)
    res = self._service.List(req)
    if res.azureNodePools:
      return True
    return False


class ClientsClient(_AzureClientBase):
  """Client for Azure Clients in the gkemulticloud API."""

  def __init__(self, **kwargs):
    super(ClientsClient, self).__init__(**kwargs)
    self._service = self._client.projects_locations_azureClients
    self._list_result_field = 'azureClients'

  def Create(self, client_ref, tenant_id, application_id, validate_only=False):
    """Creates a new Azure client."""
    req = self._messages.GkemulticloudProjectsLocationsAzureClientsCreateRequest(
        googleCloudGkemulticloudV1AzureClient=self._Client(
            applicationId=application_id,
            name=client_ref.azureClientsId,
            tenantId=tenant_id),
        azureClientId=client_ref.azureClientsId,
        parent=client_ref.Parent().RelativeName())
    if validate_only:
      req.validateOnly = True
    return self._service.Create(req)
