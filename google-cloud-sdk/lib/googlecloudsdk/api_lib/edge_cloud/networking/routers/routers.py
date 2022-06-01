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
"""Distributed Cloud Edge Network router API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import encoding
from googlecloudsdk.api_lib.edge_cloud.networking import utils
from googlecloudsdk.calliope import parser_errors
from googlecloudsdk.core import exceptions as core_exceptions


class RoutersClient(object):
  """Client for private connections service in the API."""
  # REST API Field Names for the updateMask
  FIELD_PATH_INTERFACE = 'interface'
  FIELD_PATH_BGP_PEER = 'bgp_peer'

  def __init__(self, client=None, messages=None):
    self._client = client or utils.GetClientInstance()
    self._messages = messages or utils.GetMessagesModule()
    self._service = self._client.projects_locations_zones_routers
    self._resource_parser = utils.GetResourceParser()

  def WaitForOperation(self, operation):
    """Waits for the given google.longrunning.Operation to complete."""
    return utils.WaitForOperation(operation, self._service)

  def ModifyToAddInterface(self, router_ref, args, existing):
    """Mutate the router to add an interface."""
    replacement = encoding.CopyProtoMessage(existing)
    new_interface = self._messages.Interface(name=args.interface_name)

    if args.interconnect_attachment is not None:
      attachment_ref = self._resource_parser.Create(
          'edgenetwork.projects.locations.zones.interconnectAttachments',
          interconnectAttachmentsId=args.interconnect_attachment,
          projectsId=router_ref.projectsId,
          locationsId=router_ref.locationsId,
          zonesId=router_ref.zonesId)
      if args.ip_mask_length is not None and args.ip_address is not None:
        new_interface.linkedInterconnectAttachment = attachment_ref.RelativeName(
        )
        new_interface.ipv4Cidr = '{0}/{1}'.format(args.ip_address,
                                                  args.ip_mask_length)
      else:
        raise parser_errors.ArgumentException(
            '--ip-address and --ip-mask-length must be set')

    if args.subnetwork is not None:
      subnet_ref = self._resource_parser.Create(
          'edgenetwork.projects.locations.zones.subnets',
          subnetsId=args.subnetwork,
          projectsId=router_ref.projectsId,
          locationsId=router_ref.locationsId,
          zonesId=router_ref.zonesId)
      new_interface.subnetwork = subnet_ref.RelativeName()

    if args.loopback_ip_addresses is not None:
      new_interface.loopbackIpAddresses = args.loopback_ip_addresses

    replacement.interface.append(new_interface)
    return replacement

  def ModifyToRemoveInterface(self, args, existing):
    """Mutate the router to delete a list of interfaces."""
    # Get the list of interfaces that are to be removed from args.
    input_remove_list = args.interface_names if args.interface_names else []

    # Remove interface if exists
    actual_remove_list = []
    replacement = encoding.CopyProtoMessage(existing)
    existing_router = encoding.CopyProtoMessage(existing)

    for iface in existing_router.interface:
      if iface.name in input_remove_list:
        replacement.interface.remove(iface)
        actual_remove_list.append(iface.name)

    # If there still are interfaces that we didn't find, the input is invalid.
    not_found_interface = sorted(
        set(input_remove_list) - set(actual_remove_list))
    if not_found_interface:
      error_msg = 'interface [{}] not found'.format(
          ', '.join(not_found_interface))
      raise core_exceptions.Error(error_msg)

    return replacement

  def ModifyToAddBgpPeer(self, args, existing):
    """Mutate the router to add a BGP peer."""

    replacement = encoding.CopyProtoMessage(existing)
    new_bgp_peer = self._messages.BgpPeer(
        name=args.peer_name,
        interface=args.interface,
        peerAsn=args.peer_asn,
        peerIpv4Cidr=args.peer_ipv4_range)
    replacement.bgpPeer.append(new_bgp_peer)
    return replacement

  def ModifyToRemoveBgpPeer(self, args, existing):
    """"Mutate the router to delete BGP peers."""
    input_remove_list = args.peer_names if args.peer_names else []
    actual_remove_list = []
    replacement = encoding.CopyProtoMessage(existing)
    existing_router = encoding.CopyProtoMessage(existing)

    for peer in existing_router.bgpPeer:
      if peer.name in input_remove_list:
        replacement.bgpPeer.remove(peer)
        actual_remove_list.append(peer.name)

    # If there still are bgp peers that we didn't find, the input is invalid.
    not_found_peer = sorted(set(input_remove_list) - set(actual_remove_list))
    if not_found_peer:
      error_msg = 'peer [{}] not found'.format(', '.join(not_found_peer))
      raise core_exceptions.Error(error_msg)

    return replacement

  def AddInterface(self, router_ref, args):
    """Create an interface on a router."""
    # Get current interfaces of router
    get_router_req = self._messages.EdgenetworkProjectsLocationsZonesRoutersGetRequest(
        name=router_ref.RelativeName())
    router_object = self._service.Get(get_router_req)

    # Update interfaces to add the new interface
    new_router_object = self.ModifyToAddInterface(router_ref, args,
                                                  router_object)

    update_router_req = self._messages.EdgenetworkProjectsLocationsZonesRoutersPatchRequest(
        name=router_ref.RelativeName(),
        router=new_router_object,
        updateMask=self.FIELD_PATH_INTERFACE)
    return self._service.Patch(update_router_req)

  def RemoveInterface(self, router_ref, args):
    """Remove a list of interfaces on a router."""
    # Get current interfaces of router
    get_router_req = self._messages.EdgenetworkProjectsLocationsZonesRoutersGetRequest(
        name=router_ref.RelativeName())
    router_object = self._service.Get(get_router_req)
    # Update interfaces to add the new interface
    new_router_object = self.ModifyToRemoveInterface(args, router_object)

    update_router_req = self._messages.EdgenetworkProjectsLocationsZonesRoutersPatchRequest(
        name=router_ref.RelativeName(),
        router=new_router_object,
        updateMask=self.FIELD_PATH_INTERFACE)

    return self._service.Patch(update_router_req)

  def AddBgpPeer(self, router_ref, args):
    """Mutate the router so to add a BGP peer."""
    # Get current router
    get_router_req = self._messages.EdgenetworkProjectsLocationsZonesRoutersGetRequest(
        name=router_ref.RelativeName())
    router_object = self._service.Get(get_router_req)

    # Update router object to add the new bgp peer
    new_router_object = self.ModifyToAddBgpPeer(args, router_object)

    update_router_req = self._messages.EdgenetworkProjectsLocationsZonesRoutersPatchRequest(
        name=router_ref.RelativeName(),
        router=new_router_object,
        updateMask=self.FIELD_PATH_BGP_PEER)
    return self._service.Patch(update_router_req)

  def RemoveBgpPeer(self, router_ref, args):
    """Mutate the router so to remove a BGP peer."""
    # Get current router
    get_router_req = self._messages.EdgenetworkProjectsLocationsZonesRoutersGetRequest(
        name=router_ref.RelativeName())
    router_object = self._service.Get(get_router_req)

    # Update router object to remove specified bgp peers
    new_router_object = self.ModifyToRemoveBgpPeer(args, router_object)

    update_router_req = self._messages.EdgenetworkProjectsLocationsZonesRoutersPatchRequest(
        name=router_ref.RelativeName(),
        router=new_router_object,
        updateMask=self.FIELD_PATH_BGP_PEER)
    return self._service.Patch(update_router_req)

  def GetStatus(self, router_ref):
    """Get the status of a specified router."""
    get_router_status_req = self._messages.EdgenetworkProjectsLocationsZonesRoutersDiagnoseRequest(
        name=router_ref.RelativeName())
    return self._service.Diagnose(get_router_status_req)
