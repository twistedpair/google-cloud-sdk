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
"""Utilities for gkeonprem API clients for Bare Metal cluster resources."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import encoding
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.container.gkeonprem import client
from googlecloudsdk.api_lib.container.gkeonprem import update_mask


class _BareMetalClusterClient(client.ClientBase):
  """Base class for GKE OnPrem Bare Metal API clients."""

  def _island_mode_cidr_config(self, args):
    """Constructs proto message BareMetalIslandModeCidrConfig."""
    kwargs = {
        'serviceAddressCidrBlocks':
            getattr(args, 'island_mode_service_address_cidr_blocks', None),
        'podAddressCidrBlocks':
            getattr(args, 'island_mode_pod_address_cidr_blocks', None),
    }

    if any(kwargs.values()):
      return self._messages.BareMetalIslandModeCidrConfig(**kwargs)

    return None

  def _network_config(self, args):
    """Constructs proto message BareMetalNetworkConfig."""
    kwargs = {
        'islandModeCidr': self._island_mode_cidr_config(args),
    }

    if any(kwargs.values()):
      return self._messages.BareMetalNetworkConfig(**kwargs)

    return None

  def _vip_config(self, args):
    """Constructs proto message BareMetalVipConfig."""
    kwargs = {
        'controlPlaneVip': getattr(args, 'control_plane_vip', None),
        'ingressVip': getattr(args, 'ingress_vip', None),
    }

    if any(kwargs.values()):
      return self._messages.BareMetalVipConfig(**kwargs)

    return None

  def _port_config(self, args):
    """Constructs proto message BareMetalPortConfig."""
    kwargs = {
        'controlPlaneLoadBalancerPort':
            getattr(args, 'control_plane_load_balancer_port', None),
    }

    if any(kwargs.values()):
      return self._messages.BareMetalPortConfig(**kwargs)

    return None

  def _address_pools(self, args):
    """Constructs proto message field address_pools."""
    address_pools = []
    address_pool_flag_value = getattr(args, 'metal_lb_config_address_pools',
                                      None)
    if address_pool_flag_value:
      for address_pool in address_pool_flag_value:
        address_pools.append(self._address_pool(address_pool))

    return address_pools

  def _address_pool(self, address_pool_args):
    """Constructs proto message BareMetalLoadBalancerAddressPool."""
    kwargs = {
        'addresses': address_pool_args.get('addresses', []),
        'pool': address_pool_args.get('pool', ''),
    }

    if any(kwargs.values()):
      return self._messages.BareMetalLoadBalancerAddressPool(**kwargs)

    return None

  def _metal_lb_config(self, args):
    """Constructs proto message BareMetalMetalLbConfig."""
    kwargs = {
        'addressPools': self._address_pools(args),
    }

    if any(kwargs.values()):
      return self._messages.BareMetalMetalLbConfig(**kwargs)

    return None

  def _manual_lb_config(self, args):
    """Constructs proto message BareMetalManualLbConfig."""
    kwargs = {
        'enabled': getattr(args, 'enable_manual_lb', False),
    }

    if any(kwargs.values()):
      return self._messages.BareMetalManualLbConfig(**kwargs)

    return None

  def _load_balancer_config(self, args):
    """Constructs proto message BareMetalLoadBalancerConfig."""
    kwargs = {
        'manualLbConfig': self._manual_lb_config(args),
        'metalLbConfig': self._metal_lb_config(args),
        'portConfig': self._port_config(args),
        'vipConfig': self._vip_config(args),
    }

    if any(kwargs.values()):
      return self._messages.BareMetalLoadBalancerConfig(**kwargs)

    return None

  def _lvp_config(self, args):
    """Constructs proto message BareMetalLvpConfig."""
    kwargs = {
        'path':
            getattr(args, 'lvp_share_path', None),
        'storageClass':
            getattr(args, 'lvp_share_storage_class', None),
    }

    if any(kwargs.values()):
      return self._messages.BareMetalLvpConfig(**kwargs)

    return None

  def _lvp_share_config(self, args):
    """Constructs proto message BareMetalLvpShareConfig."""
    kwargs = {
        'lvpConfig': self._lvp_config(args),
    }

    if any(kwargs.values()):
      return self._messages.BareMetalLvpShareConfig(**kwargs)

    return None

  def _lvp_node_mounts_config(self, args):
    """Constructs proto message BareMetalLvpConfig."""
    kwargs = {
        'path':
            getattr(args, 'lvp_node_mounts_config_path', None),
        'storageClass':
            getattr(args, 'lvp_node_mounts_config_storage_class', None),
    }

    if any(kwargs.values()):
      return self._messages.BareMetalLvpConfig(**kwargs)

    return None

  def _storage_config(self, args):
    """Constructs proto message BareMetalStorageConfig."""
    kwargs = {
        'lvpShareConfig': self._lvp_share_config(args),
        'lvpNodeMountsConfig': self._lvp_node_mounts_config(args),
    }

    if any(kwargs.values()):
      return self._messages.BareMetalStorageConfig(**kwargs)

    return None

  def _node_config(self, node_config_args):
    """Constructs proto message BareMetalNodeConfig."""
    kwargs = {
        'nodeIp': node_config_args.get('node-ip', ''),
    }

    if any(kwargs.values()):
      return self._messages.BareMetalNodeConfig(**kwargs)

    return None

  def _node_configs(self, args):
    """Constructs proto message field node_configs."""
    node_configs = []
    node_config_flag_value = getattr(args, 'control_plane_node_configs',
                                     None)
    if node_config_flag_value:
      for node_config in node_config_flag_value:
        node_configs.append(self._node_config(node_config))

    return node_configs

  def _node_pool_config(self, args):
    """Constructs proto message BareMetalNodePoolConfig."""
    kwargs = {
        'nodeConfigs': self._node_configs(args)
    }

    if any(kwargs.values()):
      return self._messages.BareMetalNodePoolConfig(**kwargs)

    return None

  def _control_plane_node_pool_config(self, args):
    """Constructs proto message BareMetalControlPlaneNodePoolConfig."""
    kwargs = {
        'nodePoolConfig': self._node_pool_config(args),
    }

    if any(kwargs.values()):
      return self._messages.BareMetalControlPlaneNodePoolConfig(**kwargs)

    return None

  def _control_plane_config(self, args):
    """Constructs proto message BareMetalControlPlaneConfig."""
    kwargs = {
        'nodePoolConfig': self._control_plane_node_pool_config(args),
    }

    if any(kwargs.values()):
      return self._messages.BareMetalControlPlaneConfig(**kwargs)

    return None

  def _bare_metal_user_cluster(self, args):
    """Constructs proto message Bare Metal Cluster."""
    kwargs = {
        'name': self._user_cluster_name(args),
        'adminClusterMembership': self._admin_cluster_membership_name(args),
        'description': getattr(args, 'description', None),
        'bareMetalVersion': getattr(args, 'version', None),
        'networkConfig': self._network_config(args),
        'controlPlane': self._control_plane_config(args),
        'loadBalancer': self._load_balancer_config(args),
        'storage': self._storage_config(args),
    }

    if any(kwargs.values()):
      return self._messages.BareMetalCluster(**kwargs)

    return None


class ClustersClient(_BareMetalClusterClient):
  """Client for clusters in gkeonprem bare metal API."""

  def __init__(self, **kwargs):
    super(ClustersClient, self).__init__(**kwargs)
    self._service = self._client.projects_locations_bareMetalClusters

  def List(self, location_ref, limit=None, page_size=None):
    """Lists Clusters in the GKE On-Prem Bare Metal API."""
    list_req = self._messages.GkeonpremProjectsLocationsBareMetalClustersListRequest(
        parent=location_ref.RelativeName())

    return list_pager.YieldFromList(
        self._service,
        list_req,
        field='bareMetalClusters',
        batch_size=page_size,
        limit=limit,
        batch_size_attribute='pageSize')

  def Describe(self, resource_ref):
    """Gets a GKE On-Prem Bare Metal API cluster resource."""
    req = self._messages.GkeonpremProjectsLocationsBareMetalClustersGetRequest(
        name=resource_ref.RelativeName())

    return self._service.Get(req)

  def Enroll(self, args):
    """Enrolls a bare metal cluster to Anthos."""
    kwargs = {
        'adminClusterMembership': self._admin_cluster_membership_name(args),
        'bareMetalClusterId': self._user_cluster_id(args),
        'localName': getattr(args, 'local_name', None),
    }
    enroll_bare_metal_cluster_request = self._messages.EnrollBareMetalClusterRequest(
        **kwargs)
    req = self._messages.GkeonpremProjectsLocationsBareMetalClustersEnrollRequest(
        parent=self._user_cluster_parent(args),
        enrollBareMetalClusterRequest=enroll_bare_metal_cluster_request,
    )

    return self._service.Enroll(req)

  def QueryVersionConfig(self, args):
    """Query Anthos on bare metal version configuration."""
    kwargs = {
        'createConfig_adminClusterMembership':
            self._admin_cluster_membership_name(args),
        'upgradeConfig_clusterName':
            self._user_cluster_name(args),
        'parent':
            self._location_ref(args).RelativeName(),
    }

    # This is a workaround for the limitation in apitools with nested messages.
    encoding.AddCustomJsonFieldMapping(
        self._messages
        .GkeonpremProjectsLocationsBareMetalClustersQueryVersionConfigRequest,
        'createConfig_adminClusterMembership',
        'createConfig.adminClusterMembership')
    encoding.AddCustomJsonFieldMapping(
        self._messages
        .GkeonpremProjectsLocationsBareMetalClustersQueryVersionConfigRequest,
        'upgradeConfig_clusterName', 'upgradeConfig.clusterName')

    req = self._messages.GkeonpremProjectsLocationsBareMetalClustersQueryVersionConfigRequest(
        **kwargs)
    return self._service.QueryVersionConfig(req)

  def Unenroll(self, args):
    """Unenrolls an Anthos cluster on bare metal."""
    kwargs = {
        'name': self._user_cluster_name(args),
        'force': getattr(args, 'force', None),
        'allowMissing': getattr(args, 'allow_missing', None),
    }
    req = (
        self._messages
        .GkeonpremProjectsLocationsBareMetalClustersUnenrollRequest(**kwargs))

    return self._service.Unenroll(req)

  def Delete(self, args):
    """Deletes an Anthos cluster on bare metal."""
    kwargs = {
        'name': self._user_cluster_name(args),
        'allowMissing': getattr(args, 'allow_missing', False),
        'validateOnly': getattr(args, 'validate_only', False),
        'force': getattr(args, 'force', False),
    }
    req = self._messages.GkeonpremProjectsLocationsBareMetalClustersDeleteRequest(
        **kwargs)

    return self._service.Delete(req)

  def Create(self, args):
    """Creates an Anthos cluster on bare metal."""
    kwargs = {
        'parent': self._user_cluster_parent(args),
        'validateOnly': getattr(args, 'validate_only', False),
        'bareMetalCluster': self._bare_metal_user_cluster(args),
        'bareMetalClusterId': self._user_cluster_id(args),
    }
    req = self._messages.GkeonpremProjectsLocationsBareMetalClustersCreateRequest(
        **kwargs)
    return self._service.Create(req)

  def Update(self, args):
    """Updates an Anthos cluster on bare metal."""
    kwargs = {
        'name': self._user_cluster_name(args),
        'allowMissing': getattr(args, 'allow_missing', None),
        'updateMask':
            update_mask.get_update_mask(
                args, update_mask.BARE_METAL_CLUSTER_ARGS_TO_UPDATE_MASKS),
        'validateOnly': getattr(args, 'validate_only', False),
        'bareMetalCluster': self._bare_metal_user_cluster(args),
    }
    req = self._messages.GkeonpremProjectsLocationsBareMetalClustersPatchRequest(
        **kwargs)
    return self._service.Patch(req)
