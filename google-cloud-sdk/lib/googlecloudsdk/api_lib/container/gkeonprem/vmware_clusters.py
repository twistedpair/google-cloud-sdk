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
"""Utilities for gkeonprem API clients for VMware cluster resources."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import encoding
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.container.gkeonprem import client
from googlecloudsdk.api_lib.container.gkeonprem import update_mask
from googlecloudsdk.command_lib.container.vmware import flags
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import properties


class ClustersClient(client.ClientBase):
  """Client for clusters in gkeonprem vmware API."""

  def __init__(self, **kwargs):
    super(ClustersClient, self).__init__(**kwargs)
    self._service = self._client.projects_locations_vmwareClusters

  def List(self, args):
    """Lists Clusters in the GKE On-Prem VMware API."""
    list_req = (
        self._messages.GkeonpremProjectsLocationsVmwareClustersListRequest(
            parent=self._location_name(args)))

    return list_pager.YieldFromList(
        self._service,
        list_req,
        field='vmwareClusters',
        batch_size=flags.Get(args, 'page_size'),
        limit=flags.Get(args, 'limit'),
        batch_size_attribute='pageSize',
    )

  def Enroll(self, args):
    """Enrolls a VMware cluster to Anthos."""
    kwargs = {
        'adminClusterMembership': self._admin_cluster_membership_name(args),
        'vmwareClusterId': self._user_cluster_id(args),
        'localName': flags.Get(args, 'local_name'),
    }
    enroll_vmware_cluster_request = self._messages.EnrollVmwareClusterRequest(
        **kwargs)
    req = self._messages.GkeonpremProjectsLocationsVmwareClustersEnrollRequest(
        parent=self._user_cluster_parent(args),
        enrollVmwareClusterRequest=enroll_vmware_cluster_request,
    )
    return self._service.Enroll(req)

  def Unenroll(self, args):
    """Unenrolls an Anthos cluster on VMware."""
    kwargs = {
        'name': self._user_cluster_name(args),
        'force': flags.Get(args, 'force'),
    }
    req = (
        self._messages.GkeonpremProjectsLocationsVmwareClustersUnenrollRequest(
            **kwargs))
    return self._service.Unenroll(req)

  def Delete(self, args):
    """Deletes an Anthos cluster on VMware."""
    kwargs = {
        'name': self._user_cluster_name(args),
        'allowMissing': flags.Get(args, 'allow_missing'),
        'validateOnly': flags.Get(args, 'validate_only'),
        'force': flags.Get(args, 'force'),
    }
    req = self._messages.GkeonpremProjectsLocationsVmwareClustersDeleteRequest(
        **kwargs)
    return self._service.Delete(req)

  def Create(self, args):
    """Creates an Anthos cluster on VMware."""
    kwargs = {
        'parent': self._user_cluster_parent(args),
        'validateOnly': flags.Get(args, 'validate_only'),
        'vmwareCluster': self._vmware_cluster(args),
        'vmwareClusterId': self._user_cluster_id(args),
    }
    req = self._messages.GkeonpremProjectsLocationsVmwareClustersCreateRequest(
        **kwargs)
    return self._service.Create(req)

  def Update(self, args):
    kwargs = {
        'name':
            self._user_cluster_name(args),
        'allowMissing':
            flags.Get(args, 'allow_missing'),
        'updateMask':
            update_mask.get_update_mask(
                args, update_mask.VMWARE_CLUSTER_ARGS_TO_UPDATE_MASKS),
        'validateOnly':
            flags.Get(args, 'validate_only'),
        'vmwareCluster':
            self._vmware_cluster(args),
    }
    req = self._messages.GkeonpremProjectsLocationsVmwareClustersPatchRequest(
        **kwargs)
    return self._service.Patch(req)

  def query_version_config(self, args):
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
        .GkeonpremProjectsLocationsVmwareClustersQueryVersionConfigRequest,
        'createConfig_adminClusterMembership',
        'createConfig.adminClusterMembership')
    encoding.AddCustomJsonFieldMapping(
        self._messages
        .GkeonpremProjectsLocationsVmwareClustersQueryVersionConfigRequest,
        'upgradeConfig_clusterName', 'upgradeConfig.clusterName')

    req = self._messages.GkeonpremProjectsLocationsVmwareClustersQueryVersionConfigRequest(
        **kwargs)
    return self._service.QueryVersionConfig(req)

  def _vmware_cluster(self, args):
    """Constructs proto message VmwareCluster."""
    kwargs = {
        'name': self._user_cluster_name(args),
        'adminClusterMembership': self._admin_cluster_membership_name(args),
        'description': flags.Get(args, 'description'),
        'onPremVersion': flags.Get(args, 'version'),
        'annotations': self._annotations(args),
        'controlPlaneNode': self._vmware_control_plane_node_config(args),
        'antiAffinityGroups': self._vmware_aag_config(args),
        'storage': self._vmware_storage_config(args),
        'networkConfig': self._vmware_network_config(args),
        'loadBalancer': self._vmware_load_balancer_config(args),
        'dataplaneV2': self._vmware_dataplane_v2_config(args),
        'vmTrackingEnabled': self._vm_tracking_enabled(args),
        'autoRepairConfig': self._vmware_auto_repair_config(args),
        'authorization': self._authorization(args),
    }
    if any(kwargs.values()):
      return self._messages.VmwareCluster(**kwargs)
    return None

  def _vm_tracking_enabled(self, args):
    if flags.Get(args, 'enable_vm_tracking'):
      return True
    return None

  def auto_repair_enabled(self, args):
    if flags.Get(args, 'enable_auto_repair'):
      return True
    if flags.Get(args, 'disable_auto_repair'):
      return False
    return None

  def _vmware_auto_repair_config(self, args):
    """Constructs proto message VmwareAutoRepairConfig."""
    kwargs = {
        'enabled': self.auto_repair_enabled(args),
    }
    if flags.IsSet(kwargs):
      return self._messages.VmwareAutoRepairConfig(**kwargs)
    return None

  def _cluster_users(self, args):
    """Constructs repeated proto message ClusterUser."""
    cluster_user_messages = []
    admin_users = flags.Get(args, 'admin_users')
    if admin_users:
      for admin_user in admin_users:
        cluster_user_message = self._messages.ClusterUser(username=admin_user)
        cluster_user_messages.append(cluster_user_message)
      return cluster_user_messages

    # On update, skip setting default value.
    if args.command_path[-1] == 'update':
      return None

    # On create, client side default admin user to the current gcloud user.
    gcloud_config_core_account = properties.VALUES.core.account.Get()
    if gcloud_config_core_account:
      default_admin_user_message = self._messages.ClusterUser(
          username=gcloud_config_core_account)
      cluster_user_messages.append(default_admin_user_message)
      return cluster_user_messages

    return None

  def _authorization(self, args):
    """Constructs proto message Authorization."""
    kwargs = {
        'adminUsers': self._cluster_users(args),
    }
    if flags.IsSet(kwargs):
      return self._messages.Authorization(**kwargs)
    return None

  def _dataplane_v2_enabled(self, args):
    """Constructs proto field dataplane_v2_enabled."""
    if flags.Get(args, 'enable_dataplane_v2'):
      return True
    if flags.Get(args, 'disable_dataplane_v2'):
      return False
    return None

  def _advanced_networking(self, args):
    """Constructs proto field advanced_networking."""
    if flags.Get(args, 'enable_advanced_networking'):
      return True
    if flags.Get(args, 'disable_advanced_networking'):
      return False
    return None

  def _vmware_dataplane_v2_config(self, args):
    """Constructs proto message VmwareDataplaneV2Config."""
    kwargs = {
        'dataplaneV2Enabled': flags.Get(args, 'enable_dataplane_v2'),
        'advancedNetworking': flags.Get(args, 'enable_advanced_networking'),
    }
    if flags.IsSet(kwargs):
      return self._messages.VmwareDataplaneV2Config(**kwargs)
    return None

  def _vsphere_csi_disabled(self, args):
    """Constructs proto field vsphere_csi_disabled."""
    if flags.Get(args, 'disable_vsphere_csi'):
      return True
    if flags.Get(args, 'enable_vsphere_csi'):
      return False
    return None

  def _vmware_storage_config(self, args):
    """Constructs proto message VmwareStorageConfig."""
    kwargs = {
        'vsphereCsiDisabled': self._vsphere_csi_disabled(args),
    }
    if flags.IsSet(kwargs):
      return self._messages.VmwareStorageConfig(**kwargs)
    return None

  def _aag_config_disabled(self, args):
    """Constructs proto field aag_config_disabled."""
    if flags.Get(args, 'disable_aag_config'):
      return True
    if flags.Get(args, 'enable_aag_config'):
      return False
    return None

  def _vmware_aag_config(self, args):
    """Constructs proto message VmwareAAGConfig."""
    kwargs = {
        'aagConfigDisabled': self._aag_config_disabled(args),
    }
    if flags.IsSet(kwargs):
      return self._messages.VmwareAAGConfig(**kwargs)
    return None

  def _auto_resize_enabled(self, args):
    """Constructs proto field auto_resize_config.enabled."""
    if flags.Get(args, 'enable_auto_resize'):
      return True
    if flags.Get(args, 'disable_auto_resize'):
      return False
    return None

  def _vmware_auto_resize_config(self, args):
    """Constructs proto message VmwareAutoResizeConfig."""
    kwargs = {
        'enabled': self._auto_resize_enabled(args),
    }
    if flags.IsSet(kwargs):
      return self._messages.VmwareAutoResizeConfig(**kwargs)
    return None

  def _vmware_control_plane_node_config(self, args):
    """Constructs proto message VmwareControlPlaneNodeConfig."""
    kwargs = {
        'autoResizeConfig': self._vmware_auto_resize_config(args),
        'cpus': flags.Get(args, 'cpus'),
        'memory': flags.Get(args, 'memory'),
        'replicas': flags.Get(args, 'replicas'),
    }
    if flags.IsSet(kwargs):
      return self._messages.VmwareControlPlaneNodeConfig(**kwargs)
    return None

  def _annotations(self, args):
    """Constructs proto message AnnotationsValue."""
    annotations = flags.Get(args, 'annotations')
    additional_property_messages = []
    if not annotations:
      return None

    for key, value in annotations.items():
      additional_property_messages.append(
          self._messages.VmwareCluster.AnnotationsValue.AdditionalProperty(
              key=key, value=value))

    annotation_value_message = self._messages.VmwareCluster.AnnotationsValue(
        additionalProperties=additional_property_messages)
    return annotation_value_message

  def _vmware_host_ip(self, host_ip):
    """Constructs proto message VmwareHostIp."""
    hostname = host_ip.get('hostname', None)
    if not hostname:
      raise InvalidConfigFile(
          'Missing field [hostname] in Static IP configuration file.')

    ip = host_ip.get('ip', None)
    if not ip:
      raise InvalidConfigFile(
          'Missing field [ip] in Static IP configuration file.')

    kwargs = {'hostname': hostname, 'ip': ip}
    return self._messages.VmwareHostIp(**kwargs)

  def _vmware_ip_block(self, ip_block):
    """Constructs proto message VmwareIpBlock."""
    gateway = ip_block.get('gateway', None)
    if not gateway:
      raise InvalidConfigFile(
          'Missing field [gateway] in Static IP configuration file.')

    netmask = ip_block.get('netmask', None)
    if not netmask:
      raise InvalidConfigFile(
          'Missing field [netmask] in Static IP configuration file.')

    host_ips = ip_block.get('ips', [])
    if not host_ips:
      raise InvalidConfigFile(
          'Missing field [ips] in Static IP configuration file.')

    kwargs = {
        'gateway': gateway,
        'netmask': netmask,
        'ips': [self._vmware_host_ip(host_ip) for host_ip in host_ips],
    }
    if flags.IsSet(kwargs):
      return self._messages.VmwareIpBlock(**kwargs)
    return None

  def _vmware_static_ip_config(self, args):
    """Constructs proto message VmwareStaticIpConfig."""
    if 'static_ip_config_from_file' not in args.GetSpecifiedArgsDict():
      return None

    file_content = args.static_ip_config_from_file
    static_ip_config = file_content.get('staticIpConfig', None)
    if not static_ip_config:
      raise InvalidConfigFile(
          'Missing field [staticIpConfig] in Static IP configuration file.')

    ip_blocks = static_ip_config.get('ipBlocks', [])
    if not ip_blocks:
      raise InvalidConfigFile(
          'Missing field [ipBlocks] in Static IP configuration file.')

    kwargs = {
        'ipBlocks': [self._vmware_ip_block(ip_block) for ip_block in ip_blocks],
    }
    if flags.IsSet(kwargs):
      return self._messages.VmwareStaticIpConfig(**kwargs)
    return None

  def _vmware_dhcp_ip_config(self, args):
    """Constructs proto message VmwareDhcpIpConfig."""
    kwargs = {
        'enabled': flags.Get(args, 'enable_dhcp'),
    }
    if flags.IsSet(kwargs):
      return self._messages.VmwareDhcpIpConfig(**kwargs)
    return None

  def _vmware_host_config(self, args):
    """Constructs proto message VmwareHostConfig."""
    kwargs = {
        'dnsServers': flags.Get(args, 'dns_servers', []),
        'ntpServers': flags.Get(args, 'ntp_servers', []),
    }
    if flags.IsSet(kwargs):
      return self._messages.VmwareHostConfig(**kwargs)
    return None

  def _vmware_network_config(self, args):
    """Constructs proto message VmwareNetworkConfig."""
    kwargs = {
        'serviceAddressCidrBlocks':
            flags.Get(args, 'service_address_cidr_blocks', []),
        'podAddressCidrBlocks':
            flags.Get(args, 'pod_address_cidr_blocks', []),
        'staticIpConfig':
            self._vmware_static_ip_config(args),
        'dhcpIpConfig':
            self._vmware_dhcp_ip_config(args),
        'hostConfig':
            self._vmware_host_config(args),
    }
    if any(kwargs.values()):
      return self._messages.VmwareNetworkConfig(**kwargs)
    return None

  def _vmware_load_balancer_config(self, args):
    """Constructs proto message VmwareLoadBalancerConfig."""
    kwargs = {
        'f5Config': self._vmware_f5_big_ip_config(args),
        'metalLbConfig': self._vmware_metal_lb_config(args),
        'manualLbConfig': self._vmware_manual_lb_config(args),
        'vipConfig': self._vmware_vip_config(args),
    }
    if any(kwargs.values()):
      return self._messages.VmwareLoadBalancerConfig(**kwargs)
    return None

  def _vmware_vip_config(self, args):
    """Constructs proto message VmwareVipConfig."""
    kwargs = {
        'controlPlaneVip': flags.Get(args, 'control_plane_vip'),
        'ingressVip': flags.Get(args, 'ingress_vip'),
    }
    if any(kwargs.values()):
      return self._messages.VmwareVipConfig(**kwargs)
    return None

  def _vmware_f5_big_ip_config(self, args):
    """Constructs proto message VmwareF5BigIpConfig."""
    kwargs = {
        'address': flags.Get(args, 'f5_config_address'),
        'partition': flags.Get(args, 'f5_config_partition'),
        'snatPool': flags.Get(args, 'f5_config_snat_pool'),
    }
    if any(kwargs.values()):
      return self._messages.VmwareF5BigIpConfig(**kwargs)
    return None

  def _vmware_metal_lb_config(self, args):
    """Constructs proto message VmwareMetalLbConfig."""
    kwargs = {
        'addressPools': self._address_pools(args),
    }
    if any(kwargs.values()):
      return self._messages.VmwareMetalLbConfig(**kwargs)
    return None

  def _vmware_manual_lb_config(self, args):
    """Constructs proto message VmwareManualLbConfig."""
    kwargs = {
        'controlPlaneNodePort':
            flags.Get(args, 'control_plane_node_port'),
        'ingressHttpNodePort':
            flags.Get(args, 'ingress_http_node_port'),
        'ingressHttpsNodePort':
            flags.Get(args, 'ingress_https_node_port'),
        'konnectivityServerNodePort':
            flags.Get(args, 'konnectivity_server_node_port'),
    }
    if flags.IsSet(kwargs):
      return self._messages.VmwareManualLbConfig(**kwargs)
    return None

  def _address_pools(self, args):
    """Constructs proto message field address_pools."""
    address_pools = []
    address_pool_flag_value = flags.Get(args, 'metal_lb_config_address_pools')
    if address_pool_flag_value:
      for address_pool in address_pool_flag_value:
        address_pools.append(self._vmware_address_pool(address_pool))
    return address_pools

  def _vmware_address_pool(self, address_pool_args):
    """Constructs proto message VmwareAddressPool."""
    kwargs = {
        'addresses': address_pool_args.get('addresses', []),
        'avoidBuggyIps': address_pool_args.get('avoid-buggy-ips', False),
        'manualAssign': address_pool_args.get('manual-assign', False),
        'pool': address_pool_args.get('pool', ''),
    }
    if any(kwargs.values()):
      return self._messages.VmwareAddressPool(**kwargs)
    return None


class InvalidConfigFile(exceptions.Error):
  """Invalid Argument."""
  pass
