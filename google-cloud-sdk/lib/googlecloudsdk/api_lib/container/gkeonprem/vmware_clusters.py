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


class ClustersClient(client.ClientBase):
  """Client for clusters in gkeonprem vmware API."""

  def __init__(self, **kwargs):
    super(ClustersClient, self).__init__(**kwargs)
    self._service = self._client.projects_locations_vmwareClusters

  def List(self, args):
    """Lists Clusters in the GKE On-Prem VMware API."""
    list_req = (
        self._messages.GkeonpremProjectsLocationsVmwareClustersListRequest(
            parent=self._location_ref(args).RelativeName()))

    return list_pager.YieldFromList(
        self._service,
        list_req,
        field='vmwareClusters',
        batch_size=flags.Get(args, 'page_size'),
        limit=flags.Get(args, 'limit'),
        batch_size_attribute='pageSize')

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
            args.allow_missing,
        'updateMask':
            update_mask.get_update_mask(
                args, update_mask.VMWARE_CLUSTER_ARGS_TO_UPDATE_MASKS),
        'validateOnly':
            args.validate_only,
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
        'upgradeConfig_clusterName',
        'upgradeConfig.clusterName')

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
        'networkConfig': self._vmware_network_config(args),
        'loadBalancer': self._vmware_load_balancer_config(args),
    }
    if any(kwargs.values()):
      return self._messages.VmwareCluster(**kwargs)
    return None

  def _vmware_host_ip(self, args):
    """Constructs proto message VmwareHostIp."""
    host_ips = flags.Get(args, 'host_ips', [])
    ret = []
    for host_ip_group in host_ips:
      ret.append(
          self._messages.VmwareHostIp(
              hostname=host_ip_group.get('hostname', ''),
              ip=host_ip_group.get('ip', ''),
          ))
    return ret

  def _vmware_ip_block(self, args):
    """Constructs proto message VmwareIpBlock."""
    kwargs = {
        'gateway': flags.Get(args, 'gateway'),
        'netmask': flags.Get(args, 'netmask'),
        'ips': self._vmware_host_ip(args),
    }
    if flags.IsSet(kwargs):
      return self._messages.VmwareIpBlock(**kwargs)
    return None

  def _vmware_static_ip_config(self, args):
    """Constructs proto message VmwareStaticIpConfig."""
    kwargs = {
        'ipBlocks': [self._vmware_ip_block(args)],
    }
    if flags.IsSet(kwargs):
      return self._messages.VmwareStaticIpConfig(**kwargs)
    return None

  def _vmware_dhcp_ip_config(self, args):
    """Constructs proto message VmwareDhcpIpConfig."""
    kwargs = {
        'enabled': flags.Get(args, 'enable-dhcp'),
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
        'avoidBuggyIps': address_pool_args.get('avoid_buggy_ips', False),
        'manualAssign': address_pool_args.get('manual_assign', False),
        'pool': address_pool_args.get('pool', ''),
    }
    if any(kwargs.values()):
      return self._messages.VmwareAddressPool(**kwargs)
    return None
