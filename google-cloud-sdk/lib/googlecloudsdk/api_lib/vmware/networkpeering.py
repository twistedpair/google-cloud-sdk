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
"""VMware Engine VPC network peering client."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import uuid

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.vmware import util
from googlecloudsdk.api_lib.vmware.networks import NetworksClient
from googlecloudsdk.command_lib.util.apis import arg_utils


class NetworkPeeringClient(util.VmwareClientBase):
  """VMware Engine VPC network peering client."""

  def __init__(self):
    super(NetworkPeeringClient, self).__init__()
    self.service = self.client.projects_locations_global_networkPeerings
    self.networks_client = NetworksClient()

  def Get(self, resource):
    request = self.messages.VmwareengineProjectsLocationsGlobalNetworkPeeringsGetRequest(
        name=resource.RelativeName())
    response = self.service.Get(request)
    return response

  def Create(self,
             resource,
             description=None,
             vmware_engine_network_id=None,
             peer_network_id=None,
             peer_network_type=None,
             peer_project=None,
             peer_mtu=None,
             export_custom_routes=True,
             import_custom_routes=True,
             export_custom_routes_with_public_ip=True,
             import_custom_routes_with_public_ip=True,
             exchange_subnet_routes=True):
    project = resource.Parent().Name()
    if peer_project is None:
      peer_project = project

    parent = '/'.join(resource.RelativeName().split('/')[:-2])
    peering_id = resource.Name()
    peering = self.messages.NetworkPeering(description=description)
    peer_network_type_enum = arg_utils.ChoiceEnumMapper(
        arg_name='peer-network-type',
        message_enum=self.messages.NetworkPeering
        .PeerNetworkTypeValueValuesEnum,
        include_filter=lambda x: 'UNSPECIFIED' not in x).GetEnumForChoice(
            arg_utils.EnumNameToChoice(peer_network_type))
    peering.peerNetworkType = peer_network_type_enum
    if vmware_engine_network_id is not None:
      ven = self.networks_client.GetByID(project, vmware_engine_network_id)
      peering.vmwareEngineNetwork = ven.name
    if peer_network_id is not None:
      if peer_network_type_enum == self.messages.NetworkPeering.PeerNetworkTypeValueValuesEnum.VMWARE_ENGINE_NETWORK:
        peering.peerNetwork = 'projects/{project}/locations/global/vmwareEngineNetworks/{network_id}'.format(
            project=peer_project, network_id=peer_network_id)
      else:
        peering.peerNetwork = 'projects/{project}/global/networks/{network_id}'.format(
            project=peer_project, network_id=peer_network_id)
    if peer_mtu:
      peering.peer_mtu = peer_mtu
    peering.exportCustomRoutes = export_custom_routes
    peering.importCustomRoutes = import_custom_routes
    peering.exportCustomRoutesWithPublicIp = export_custom_routes_with_public_ip
    peering.importCustomRoutesWithPublicIp = import_custom_routes_with_public_ip
    peering.exchangeSubnetRoutes = exchange_subnet_routes
    request = self.messages.VmwareengineProjectsLocationsGlobalNetworkPeeringsCreateRequest(
        parent=parent,
        networkPeering=peering,
        networkPeeringId=peering_id,
        requestId=uuid.uuid4().hex)

    return self.service.Create(request)

  def Update(self, resource, description=None):
    peering = self.Get(resource)
    update_mask = []
    if description is not None:
      peering.description = description
      update_mask.append('description')
    request = self.messages.VmwareengineProjectsLocationsGlobalNetworkPeeringsPatchRequest(
        networkPeering=peering,
        name=resource.RelativeName(),
        updateMask=','.join(update_mask),
        requestId=uuid.uuid4().hex)
    return self.service.Patch(request)

  def Delete(self, resource, delay_hours=None):
    return self.service.Delete(
        self.messages
        .VmwareengineProjectsLocationsGlobalNetworkPeeringsDeleteRequest(
            name=resource.RelativeName(), requestId=uuid.uuid4().hex))

  def List(self,
           location_resource,
           filter_expression=None,
           limit=None,
           page_size=None,
           sort_by=None):
    location = location_resource.RelativeName()
    request = self.messages.VmwareengineProjectsLocationsGlobalNetworkPeeringsListRequest(
        parent=location, filter=filter_expression)
    if page_size:
      request.page_size = page_size
    return list_pager.YieldFromList(
        self.service,
        request,
        limit=limit,
        batch_size_attribute='pageSize',
        batch_size=page_size,
        field='networkPeerings')
