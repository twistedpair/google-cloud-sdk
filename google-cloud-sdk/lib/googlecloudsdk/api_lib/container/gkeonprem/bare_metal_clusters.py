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
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import properties


class _BareMetalClusterClient(client.ClientBase):
  """Base class for GKE OnPrem Bare Metal API clients."""

  def _annotations(self, args):
    """Constructs proto message AnnotationsValue."""
    annotations = getattr(args, 'annotations', {})
    additional_property_messages = []
    if not annotations:
      return None

    for key, value in annotations.items():
      additional_property_messages.append(
          self._messages.BareMetalCluster.AnnotationsValue.AdditionalProperty(
              key=key, value=value
          )
      )

    annotation_value_message = self._messages.BareMetalCluster.AnnotationsValue(
        additionalProperties=additional_property_messages
    )
    return annotation_value_message

  def _island_mode_cidr_config(self, args):
    """Constructs proto message BareMetalIslandModeCidrConfig."""
    kwargs = {
        'serviceAddressCidrBlocks': getattr(
            args, 'island_mode_service_address_cidr_blocks', []
        ),
        'podAddressCidrBlocks': getattr(
            args, 'island_mode_pod_address_cidr_blocks', []
        ),
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
        'controlPlaneLoadBalancerPort': getattr(
            args, 'control_plane_load_balancer_port', None
        ),
    }

    if any(kwargs.values()):
      return self._messages.BareMetalPortConfig(**kwargs)

    return None

  def _address_pools_from_file(self, args):
    """Constructs proto message field address_pools."""
    if not args.metal_lb_address_pools_from_file:
      return []

    address_pools = args.metal_lb_address_pools_from_file.get(
        'addressPools', []
    )

    if not address_pools:
      raise exceptions.BadArgumentException(
          '--metal_lb_address_pools_from_file',
          'Missing field [addressPools] in Metal LB address pools file.',
      )

    address_pool_messages = []
    for address_pool in address_pools:
      address_pool_messages.append(self._address_pool(address_pool))

    return address_pool_messages

  def _address_pool(self, address_pool):
    """Constructs proto message BareMetalLoadBalancerAddressPool."""
    addresses = address_pool.get('addresses', [])
    if not addresses:
      raise exceptions.BadArgumentException(
          '--metal_lb_address_pools_from_file',
          'Missing field [addresses] in Metal LB address pools file.',
      )

    pool = address_pool.get('pool', None)
    if not pool:
      raise exceptions.BadArgumentException(
          '--metal_lb_address_pools_from_file',
          'Missing field [pool] in Metal LB address pools file.',
      )

    kwargs = {
        'addresses': addresses,
        'avoidBuggyIps': address_pool.get('avoidBuggyIPs', None),
        'manualAssign': address_pool.get('manualAssign', None),
        'pool': pool,
    }

    return self._messages.BareMetalLoadBalancerAddressPool(**kwargs)

  def _address_pools_from_flag(self, args):
    if not args.metal_lb_address_pools:
      return []

    address_pools = []
    for address_pool in args.metal_lb_address_pools:
      address_pools.append(
          self._messages.BareMetalLoadBalancerAddressPool(
              addresses=address_pool.get('addresses', []),
              avoidBuggyIps=address_pool.get('avoid-buggy-ips', None),
              manualAssign=address_pool.get('manual-assign', None),
              pool=address_pool.get('pool', None),
          )
      )

    return address_pools

  def _metal_lb_node_config(self, metal_lb_node_config):
    """Constructs proto message BareMetalNodeConfig."""
    node_ip = metal_lb_node_config.get('nodeIP', '')
    if not node_ip:
      raise exceptions.BadArgumentException(
          '--metal_lb_load_balancer_node_configs_from_file',
          'Missing field [nodeIP] in Metal LB Node configs file.',
      )

    kwargs = {
        'nodeIp': node_ip,
        'labels': self._node_labels(metal_lb_node_config.get('labels', {})),
    }

    return self._messages.BareMetalNodeConfig(**kwargs)

  def _metal_lb_node_configs_from_file(self, args):
    """Constructs proto message field node_configs."""
    if not args.metal_lb_load_balancer_node_configs_from_file:
      return []

    metal_lb_node_configs = (
        args.metal_lb_load_balancer_node_configs_from_file.get(
            'nodeConfigs', []
        )
    )

    if not metal_lb_node_configs:
      raise exceptions.BadArgumentException(
          '--metal_lb_load_balancer_node_configs_from_file',
          'Missing field [nodeConfigs] in Metal LB Node configs file.',
      )

    metal_lb_node_configs_messages = []
    for metal_lb_node_config in metal_lb_node_configs:
      metal_lb_node_configs_messages.append(
          self._metal_lb_node_config(metal_lb_node_config)
      )

    return metal_lb_node_configs_messages

  def parse_node_labels(self, node_labels):
    """Validates and parses a node label object.

    Args:
      node_labels: str of key-val pairs separated by ';' delimiter.

    Returns:
      If label is valid, returns a dict mapping message LabelsValue to its
      value, otherwise, raise ArgumentTypeError.
      For example,
      {
          'key': LABEL_KEY
          'value': LABEL_VALUE
      }
    """
    if not node_labels.get('labels'):
      return None

    input_node_labels = node_labels.get('labels', '').split(';')
    additional_property_messages = []

    for label in input_node_labels:
      key_val_pair = label.split('=')
      if len(key_val_pair) != 2:
        raise arg_parsers.ArgumentTypeError(
            'Node Label [{}] not in correct format, expect KEY=VALUE.'.format(
                input_node_labels
            )
        )
      additional_property_messages.append(
          self._messages.BareMetalNodeConfig.LabelsValue.AdditionalProperty(
              key=key_val_pair[0], value=key_val_pair[1]
          )
      )

    labels_value_message = self._messages.BareMetalNodeConfig.LabelsValue(
        additionalProperties=additional_property_messages
    )

    return labels_value_message

  def node_config(self, node_config_args):
    """Constructs proto message BareMetalNodeConfig."""
    kwargs = {
        'nodeIp': node_config_args.get('node-ip', ''),
        'labels': self.parse_node_labels(node_config_args),
    }

    if any(kwargs.values()):
      return self._messages.BareMetalNodeConfig(**kwargs)

    return None

  def _metal_lb_node_configs_from_flag(self, args):
    """Constructs proto message field node_configs."""
    node_config_flag_value = (
        getattr(args, 'metal_lb_load_balancer_node_configs', [])
        if args.metal_lb_load_balancer_node_configs
        else []
    )

    return [
        self.node_config(node_config) for node_config in node_config_flag_value
    ]

  def _metal_lb_node_taints(self, args):
    """Constructs proto message NodeTaint."""
    taint_messages = []
    node_taints = getattr(args, 'metal_lb_load_balancer_node_taints', {})
    if not node_taints:
      return []

    for node_taint in node_taints.items():
      taint_object = self._parse_node_taint(node_taint)
      taint_messages.append(self._messages.NodeTaint(**taint_object))

    return taint_messages

  def _metal_lb_labels(self, args):
    """Constructs proto message LabelsValue."""
    node_labels = getattr(args, 'metal_lb_load_balancer_node_labels', {})
    additional_property_messages = []

    if not node_labels:
      return None

    for key, value in node_labels.items():
      additional_property_messages.append(
          self._messages.BareMetalNodePoolConfig.LabelsValue.AdditionalProperty(
              key=key, value=value
          )
      )

    labels_value_message = self._messages.BareMetalNodePoolConfig.LabelsValue(
        additionalProperties=additional_property_messages
    )

    return labels_value_message

  def _metal_lb_load_balancer_node_pool_config(self, args):
    """Constructs proto message BareMetalNodePoolConfig."""
    if (
        'metal_lb_load_balancer_node_configs_from_file'
        in args.GetSpecifiedArgsDict()
    ):
      metal_lb_node_configs = self._metal_lb_node_configs_from_file(args)
    else:
      metal_lb_node_configs = self._metal_lb_node_configs_from_flag(args)

    kwargs = {
        'nodeConfigs': metal_lb_node_configs,
        'labels': self._metal_lb_labels(args),
        'taints': self._metal_lb_node_taints(args),
    }

    if any(kwargs.values()):
      return self._messages.BareMetalNodePoolConfig(**kwargs)

    return None

  def _metal_lb_node_pool_config(self, args):
    """Constructs proto message BareMetalLoadBalancerNodePoolConfig."""
    kwargs = {
        'nodePoolConfig': self._metal_lb_load_balancer_node_pool_config(args),
    }

    if any(kwargs.values()):
      return self._messages.BareMetalLoadBalancerNodePoolConfig(**kwargs)

    return None

  def _metal_lb_config(self, args):
    """Constructs proto message BareMetalMetalLbConfig."""
    if 'metal_lb_address_pools_from_file' in args.GetSpecifiedArgsDict():
      address_pools = self._address_pools_from_file(args)
    else:
      address_pools = self._address_pools_from_flag(args)
    kwargs = {
        'addressPools': address_pools,
        'loadBalancerNodePoolConfig': self._metal_lb_node_pool_config(args),
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
        'path': getattr(args, 'lvp_share_path', None),
        'storageClass': getattr(args, 'lvp_share_storage_class', None),
    }

    if any(kwargs.values()):
      return self._messages.BareMetalLvpConfig(**kwargs)

    return None

  def _lvp_share_config(self, args):
    """Constructs proto message BareMetalLvpShareConfig."""
    kwargs = {
        'lvpConfig': self._lvp_config(args),
        'sharedPathPvCount': getattr(args, 'lvp_share_path_pv_count', None),
    }

    if any(kwargs.values()):
      return self._messages.BareMetalLvpShareConfig(**kwargs)

    return None

  def _lvp_node_mounts_config(self, args):
    """Constructs proto message BareMetalLvpConfig."""
    kwargs = {
        'path': getattr(args, 'lvp_node_mounts_config_path', None),
        'storageClass': getattr(
            args, 'lvp_node_mounts_config_storage_class', None
        ),
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

  def _node_labels(self, labels):
    """Constructs proto message LabelsValue."""
    additional_property_messages = []
    if not labels:
      return None

    for key, value in labels.items():
      additional_property_messages.append(
          self._messages.BareMetalNodeConfig.LabelsValue.AdditionalProperty(
              key=key, value=value
          )
      )

    labels_value_message = self._messages.BareMetalNodeConfig.LabelsValue(
        additionalProperties=additional_property_messages
    )

    return labels_value_message

  def _control_plane_node_config(self, control_plane_node_config):
    """Constructs proto message BareMetalNodeConfig."""
    node_ip = control_plane_node_config.get('nodeIP', '')
    if not node_ip:
      raise exceptions.BadArgumentException(
          '--control_plane_node_configs_from_file',
          'Missing field [nodeIP] in Control Plane Node configs file.',
      )

    kwargs = {
        'nodeIp': node_ip,
        'labels': self._node_labels(
            control_plane_node_config.get('labels', {})
        ),
    }

    return self._messages.BareMetalNodeConfig(**kwargs)

  def _control_plane_node_configs_from_file(self, args):
    """Constructs proto message field node_configs."""
    if not args.control_plane_node_configs_from_file:
      return []

    control_plane_node_configs = args.control_plane_node_configs_from_file.get(
        'nodeConfigs', []
    )

    if not control_plane_node_configs:
      raise exceptions.BadArgumentException(
          '--control_plane_node_configs_from_file',
          'Missing field [nodeConfigs] in Control Plane Node configs file.',
      )

    control_plane_node_configs_messages = []
    for control_plane_node_config in control_plane_node_configs:
      control_plane_node_configs_messages.append(
          self._control_plane_node_config(control_plane_node_config)
      )

    return control_plane_node_configs_messages

  def _control_plane_node_configs_from_flag(self, args):
    """Constructs proto message field node_configs."""
    node_configs = []
    node_config_flag_value = getattr(args, 'control_plane_node_configs', None)
    if node_config_flag_value:
      for node_config in node_config_flag_value:
        node_configs.append(self.node_config(node_config))

    return node_configs

  def _control_plane_node_taints(self, args):
    """Constructs proto message NodeTaint."""
    taint_messages = []
    node_taints = getattr(args, 'control_plane_node_taints', {})
    if not node_taints:
      return []

    for node_taint in node_taints.items():
      taint_object = self._parse_node_taint(node_taint)
      taint_messages.append(self._messages.NodeTaint(**taint_object))

    return taint_messages

  def _control_plane_node_labels(self, args):
    """Constructs proto message LabelsValue."""
    node_labels = getattr(args, 'control_plane_node_labels', {})
    additional_property_messages = []
    if not node_labels:
      return None

    for key, value in node_labels.items():
      additional_property_messages.append(
          self._messages.BareMetalNodePoolConfig.LabelsValue.AdditionalProperty(
              key=key, value=value
          )
      )

    labels_value_message = self._messages.BareMetalNodePoolConfig.LabelsValue(
        additionalProperties=additional_property_messages
    )

    return labels_value_message

  def _node_pool_config(self, args):
    """Constructs proto message BareMetalNodePoolConfig."""
    if 'control_plane_node_configs_from_file' in args.GetSpecifiedArgsDict():
      node_configs = self._control_plane_node_configs_from_file(args)
    else:
      node_configs = self._control_plane_node_configs_from_flag(args)

    kwargs = {
        'nodeConfigs': node_configs,
        'labels': self._control_plane_node_labels(args),
        'taints': self._control_plane_node_taints(args),
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

  def _api_server_args(self, args):
    """Constructs proto message BareMetalApiServerArgument."""
    api_server_args = []
    api_server_args_flag_value = getattr(args, 'api_server_args', None)
    if api_server_args_flag_value:
      for key, val in api_server_args_flag_value.items():
        api_server_args.append(
            self._messages.BareMetalApiServerArgument(argument=key, value=val)
        )

    return api_server_args

  def _control_plane_config(self, args):
    """Constructs proto message BareMetalControlPlaneConfig."""
    kwargs = {
        'controlPlaneNodePoolConfig': self._control_plane_node_pool_config(
            args
        ),
        'apiServerArgs': self._api_server_args(args),
    }

    if any(kwargs.values()):
      return self._messages.BareMetalControlPlaneConfig(**kwargs)

    return None

  def _proxy_config(self, args):
    """Constructs proto message BareMetalProxyConfig."""
    kwargs = {
        'uri': getattr(args, 'uri', None),
        'noProxy': getattr(args, 'no_proxy', []),
    }

    if any(kwargs.values()):
      return self._messages.BareMetalProxyConfig(**kwargs)

    return None

  def _cluster_operations_config(self, args):
    """Constructs proto message BareMetalClusterOperationsConfig."""
    kwargs = {
        'enableApplicationLogs': getattr(args, 'enable_application_logs', None),
    }

    if any(kwargs.values()):
      return self._messages.BareMetalClusterOperationsConfig(**kwargs)

    return None

  def _maintenance_config(self, args):
    """Constructs proto message BareMetalMaintenanceConfig."""
    kwargs = {
        'maintenanceAddressCidrBlocks': getattr(
            args, 'maintenance_address_cidr_blocks', []
        ),
    }

    if any(kwargs.values()):
      return self._messages.BareMetalMaintenanceConfig(**kwargs)

    return None

  def _container_runtime(self, container_runtime):
    """Constructs proto message BareMetalWorkloadNodeConfig.ContainerRuntimeValueValuesEnum."""
    if container_runtime is None:
      return None

    container_runtime_enum = (
        self._messages.BareMetalWorkloadNodeConfig.ContainerRuntimeValueValuesEnum
    )
    container_runtime_mapping = {
        'ContainerRuntimeUnspecified': (
            container_runtime_enum.CONTAINER_RUNTIME_UNSPECIFIED
        ),
        'Conatinerd': container_runtime_enum.CONTAINERD,
    }

    return container_runtime_mapping[container_runtime]

  def _workload_node_config(self, args):
    """Constructs proto message BareMetalWorkloadNodeConfig."""
    container_runtime = getattr(args, 'container_runtime', None)
    kwargs = {
        'containerRuntime': self._container_runtime(container_runtime),
        'maxPodsPerNode': getattr(args, 'max_pods_per_node', None),
    }

    if any(kwargs.values()):
      return self._messages.BareMetalWorkloadNodeConfig(**kwargs)

    return None

  # TODO(b/257292798): Move to common directory
  def _cluster_users(self, args):
    """Constructs repeated proto message ClusterUser."""
    cluster_user_messages = []
    admin_users = getattr(args, 'admin_users', None)
    if admin_users:
      return [
          self._messages.ClusterUser(username=admin_user)
          for admin_user in admin_users
      ]

    # On update, skip setting default value.
    if args.command_path[-1] == 'update':
      return None

    # On create, client side default admin user to the current gcloud user.
    gcloud_config_core_account = properties.VALUES.core.account.Get()
    if gcloud_config_core_account:
      default_admin_user_message = self._messages.ClusterUser(
          username=gcloud_config_core_account
      )
      return cluster_user_messages.append(default_admin_user_message)

    return None

  def _authorization(self, args):
    """Constructs proto message Authorization."""
    kwargs = {
        'adminUsers': self._cluster_users(args),
    }

    if any(kwargs.values()):
      return self._messages.Authorization(**kwargs)

    return None

  def _security_config(self, args):
    """Constructs proto message BareMetalSecurityConfig."""
    kwargs = {
        'authorization': self._authorization(args),
    }

    if any(kwargs.values()):
      return self._messages.BareMetalSecurityConfig(**kwargs)

    return None

  def _node_access_config(self, args):
    """Constructs proto message BareMetalNodeAccessConfig."""
    kwargs = {
        'loginUser': getattr(args, 'login_user', 'root'),
    }

    if any(kwargs.values()):
      return self._messages.BareMetalNodeAccessConfig(**kwargs)

    return None

  def _bare_metal_user_cluster(self, args):
    """Constructs proto message Bare Metal Cluster."""
    kwargs = {
        'name': self._user_cluster_name(args),
        'adminClusterMembership': self._admin_cluster_membership_name(args),
        'description': getattr(args, 'description', None),
        'annotations': self._annotations(args),
        'bareMetalVersion': getattr(args, 'version', None),
        'networkConfig': self._network_config(args),
        'controlPlane': self._control_plane_config(args),
        'loadBalancer': self._load_balancer_config(args),
        'storage': self._storage_config(args),
        'proxy': self._proxy_config(args),
        'clusterOperations': self._cluster_operations_config(args),
        'maintenanceConfig': self._maintenance_config(args),
        'nodeConfig': self._workload_node_config(args),
        'securityConfig': self._security_config(args),
        'nodeAccessConfig': self._node_access_config(args),
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
    list_req = (
        self._messages.GkeonpremProjectsLocationsBareMetalClustersListRequest(
            parent=location_ref.RelativeName()
        )
    )

    return list_pager.YieldFromList(
        self._service,
        list_req,
        field='bareMetalClusters',
        batch_size=page_size,
        limit=limit,
        batch_size_attribute='pageSize',
    )

  def Describe(self, resource_ref):
    """Gets a GKE On-Prem Bare Metal API cluster resource."""
    req = self._messages.GkeonpremProjectsLocationsBareMetalClustersGetRequest(
        name=resource_ref.RelativeName()
    )

    return self._service.Get(req)

  def Enroll(self, args):
    """Enrolls a bare metal cluster to Anthos."""
    kwargs = {
        'adminClusterMembership': self._admin_cluster_membership_name(args),
        'bareMetalClusterId': self._user_cluster_id(args),
        'localName': getattr(args, 'local_name', None),
    }
    enroll_bare_metal_cluster_request = (
        self._messages.EnrollBareMetalClusterRequest(**kwargs)
    )
    req = (
        self._messages.GkeonpremProjectsLocationsBareMetalClustersEnrollRequest(
            parent=self._user_cluster_parent(args),
            enrollBareMetalClusterRequest=enroll_bare_metal_cluster_request,
        )
    )

    return self._service.Enroll(req)

  def QueryVersionConfig(self, args):
    """Query Anthos on bare metal version configuration."""
    kwargs = {
        'createConfig_adminClusterMembership': (
            self._admin_cluster_membership_name(args)
        ),
        'upgradeConfig_clusterName': self._user_cluster_name(args),
        'parent': self._location_ref(args).RelativeName(),
    }

    # This is a workaround for the limitation in apitools with nested messages.
    encoding.AddCustomJsonFieldMapping(
        self._messages.GkeonpremProjectsLocationsBareMetalClustersQueryVersionConfigRequest,
        'createConfig_adminClusterMembership',
        'createConfig.adminClusterMembership',
    )
    encoding.AddCustomJsonFieldMapping(
        self._messages.GkeonpremProjectsLocationsBareMetalClustersQueryVersionConfigRequest,
        'upgradeConfig_clusterName',
        'upgradeConfig.clusterName',
    )

    req = self._messages.GkeonpremProjectsLocationsBareMetalClustersQueryVersionConfigRequest(
        **kwargs
    )
    return self._service.QueryVersionConfig(req)

  def Unenroll(self, args):
    """Unenrolls an Anthos cluster on bare metal."""
    kwargs = {
        'name': self._user_cluster_name(args),
        'force': getattr(args, 'force', None),
        'allowMissing': getattr(args, 'allow_missing', None),
    }
    req = self._messages.GkeonpremProjectsLocationsBareMetalClustersUnenrollRequest(
        **kwargs
    )

    return self._service.Unenroll(req)

  def Delete(self, args):
    """Deletes an Anthos cluster on bare metal."""
    kwargs = {
        'name': self._user_cluster_name(args),
        'allowMissing': getattr(args, 'allow_missing', False),
        'validateOnly': getattr(args, 'validate_only', False),
        'force': getattr(args, 'force', False),
        'ignoreErrors': self.GetFlag(args, 'ignore_errors'),
    }
    req = (
        self._messages.GkeonpremProjectsLocationsBareMetalClustersDeleteRequest(
            **kwargs
        )
    )

    return self._service.Delete(req)

  def Create(self, args):
    """Creates an Anthos cluster on bare metal."""
    kwargs = {
        'parent': self._user_cluster_parent(args),
        'validateOnly': getattr(args, 'validate_only', False),
        'bareMetalCluster': self._bare_metal_user_cluster(args),
        'bareMetalClusterId': self._user_cluster_id(args),
    }
    req = (
        self._messages.GkeonpremProjectsLocationsBareMetalClustersCreateRequest(
            **kwargs
        )
    )

    return self._service.Create(req)

  def Update(self, args):
    """Updates an Anthos cluster on bare metal."""
    kwargs = {
        'name': self._user_cluster_name(args),
        'allowMissing': getattr(args, 'allow_missing', None),
        'updateMask': update_mask.get_update_mask(
            args, update_mask.BARE_METAL_CLUSTER_ARGS_TO_UPDATE_MASKS
        ),
        'validateOnly': getattr(args, 'validate_only', False),
        'bareMetalCluster': self._bare_metal_user_cluster(args),
    }
    req = (
        self._messages.GkeonpremProjectsLocationsBareMetalClustersPatchRequest(
            **kwargs
        )
    )

    return self._service.Patch(req)
