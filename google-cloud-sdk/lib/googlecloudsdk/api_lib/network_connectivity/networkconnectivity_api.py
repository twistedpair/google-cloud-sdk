# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Commands for interacting with the Network Connectivity API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.network_connectivity import networkconnectivity_util
from googlecloudsdk.calliope import base


class SpokesClient(object):
  """Client for spoke service in network connectivity API."""

  def __init__(self, release_track=base.ReleaseTrack.GA):
    self.release_track = release_track
    self.client = networkconnectivity_util.GetClientInstance(release_track)
    self.messages = networkconnectivity_util.GetMessagesModule(release_track)
    self.spoke_service = self.client.projects_locations_spokes
    self.operation_service = self.client.projects_locations_operations

  def Activate(self, spoke_ref):
    """Call API to activate an existing spoke."""
    activate_req = (
        self.messages.NetworkconnectivityProjectsLocationsSpokesActivateRequest(
            name=spoke_ref.RelativeName()
        )
    )
    return self.spoke_service.Activate(activate_req)

  def Deactivate(self, spoke_ref):
    """Call API to deactivate an existing spoke."""
    deactivate_req = self.messages.NetworkconnectivityProjectsLocationsSpokesDeactivateRequest(
        name=spoke_ref.RelativeName()
    )
    return self.spoke_service.Deactivate(deactivate_req)

  def Delete(self, spoke_ref):
    """Call API to delete an existing spoke."""
    delete_req = (
        self.messages.NetworkconnectivityProjectsLocationsSpokesDeleteRequest(
            name=spoke_ref.RelativeName()
        )
    )
    return self.spoke_service.Delete(delete_req)

  def Get(self, spoke_ref):
    """Call API to get an existing spoke."""
    get_req = (
        self.messages.NetworkconnectivityProjectsLocationsSpokesGetRequest(
            name=spoke_ref.RelativeName()
        )
    )
    return self.spoke_service.Get(get_req)

  def List(
      self,
      region_ref,
      limit=None,
      filter_expression=None,
      order_by='',
      page_size=None,
      page_token=None,
  ):
    """Call API to list spokes."""
    list_req = (
        self.messages.NetworkconnectivityProjectsLocationsSpokesListRequest(
            parent=region_ref.RelativeName(),
            filter=filter_expression,
            orderBy=order_by,
            pageSize=page_size,
            pageToken=page_token,
        )
    )
    return list_pager.YieldFromList(
        self.spoke_service,
        list_req,
        field='spokes',
        limit=limit,
        batch_size_attribute='pageSize',
    )

  def CreateSpoke(self, spoke_ref, spoke, request_id=None):
    """Call API to create a new spoke."""
    parent = spoke_ref.Parent().RelativeName()
    spoke_id = spoke_ref.Name()

    create_req = (
        self.messages.NetworkconnectivityProjectsLocationsSpokesCreateRequest(
            parent=parent, requestId=request_id, spoke=spoke, spokeId=spoke_id
        )
    )
    return self.spoke_service.Create(create_req)

  def CreateSpokeBeta(self, spoke_ref, spoke, request_id=None):
    """Call API to create a new spoke."""
    parent = spoke_ref.Parent().RelativeName()
    spoke_id = spoke_ref.Name()

    create_req = (
        self.messages.NetworkconnectivityProjectsLocationsSpokesCreateRequest(
            parent=parent,
            requestId=request_id,
            googleCloudNetworkconnectivityV1betaSpoke=spoke,
            spokeId=spoke_id,
        )
    )
    return self.spoke_service.Create(create_req)

  def UpdateSpoke(self, spoke_ref, spoke, update_mask, request_id=None):
    """Call API to update a existing spoke."""
    name = spoke_ref.RelativeName()
    update_mask_string = ','.join(update_mask)

    update_req = (
        self.messages.NetworkconnectivityProjectsLocationsSpokesPatchRequest(
            name=name,
            requestId=request_id,
            spoke=spoke,
            updateMask=update_mask_string,
        )
    )
    return self.spoke_service.Patch(update_req)

  def UpdateSpokeBeta(self, spoke_ref, spoke, update_mask, request_id=None):
    """Call API to update a existing spoke."""
    name = spoke_ref.RelativeName()
    update_mask_string = ','.join(update_mask)

    update_req = (
        self.messages.NetworkconnectivityProjectsLocationsSpokesPatchRequest(
            name=name,
            requestId=request_id,
            googleCloudNetworkconnectivityV1betaSpoke=spoke,
            updateMask=update_mask_string,
        )
    )
    return self.spoke_service.Patch(update_req)


class HubsClient(object):
  """Client for hub service in network connectivity API."""

  def __init__(self, release_track=base.ReleaseTrack.GA):
    self.release_track = release_track
    self.client = networkconnectivity_util.GetClientInstance(release_track)
    self.messages = networkconnectivity_util.GetMessagesModule(release_track)
    self.hub_service = self.client.projects_locations_global_hubs
    self.operation_service = self.client.projects_locations_operations

  def ListHubSpokes(
      self,
      hub_ref,
      spoke_locations=None,
      limit=None,
      filter_expression=None,
      order_by='',
      # If page_size is set to None, ListHubSpokes will return all spokes
      # (defaults to 500). Accordingly, pagination will be handled on the client
      # side.
      page_size=None,
      page_token=None,
      view=None,
  ):
    """Call API to list spokes."""
    list_req = self.messages.NetworkconnectivityProjectsLocationsGlobalHubsListSpokesRequest(
        name=hub_ref.RelativeName(),
        spokeLocations=spoke_locations,
        filter=filter_expression,
        orderBy=order_by,
        pageSize=page_size,
        pageToken=page_token,
        view=view,
    )
    return list_pager.YieldFromList(
        self.hub_service,
        list_req,
        field='spokes',
        limit=limit,
        batch_size_attribute='pageSize',
        method='ListSpokes',
    )

  def AcceptSpoke(self, hub_ref, spoke):
    """Call API to accept a spoke into a hub in the GA release track."""
    accept_hub_spoke_req = self.messages.AcceptHubSpokeRequest(spokeUri=spoke)
    accept_req = self.messages.NetworkconnectivityProjectsLocationsGlobalHubsAcceptSpokeRequest(
        name=hub_ref.RelativeName(), acceptHubSpokeRequest=accept_hub_spoke_req
    )
    return self.hub_service.AcceptSpoke(accept_req)

  def AcceptSpokeBeta(self, hub_ref, spoke):
    """Call API to accept a spoke into a hub in the BETA release track."""
    accept_hub_spoke_req = (
        self.messages.GoogleCloudNetworkconnectivityV1betaAcceptHubSpokeRequest(
            spokeUri=spoke
        )
    )
    accept_req = self.messages.NetworkconnectivityProjectsLocationsGlobalHubsAcceptSpokeRequest(
        name=hub_ref.RelativeName(),
        googleCloudNetworkconnectivityV1betaAcceptHubSpokeRequest=accept_hub_spoke_req,
    )
    return self.hub_service.AcceptSpoke(accept_req)

  def RejectSpoke(self, hub_ref, spoke, details):
    """Call API to reject a spoke from a hub in the GA release track."""
    reject_hub_spoke_req = self.messages.RejectHubSpokeRequest(
        spokeUri=spoke, details=details
    )
    reject_req = self.messages.NetworkconnectivityProjectsLocationsGlobalHubsRejectSpokeRequest(
        name=hub_ref.RelativeName(), rejectHubSpokeRequest=reject_hub_spoke_req
    )
    return self.hub_service.RejectSpoke(reject_req)

  def RejectSpokeBeta(self, hub_ref, spoke, details):
    """Call API to reject a spoke from a hub in the BETA release track."""
    reject_hub_spoke_req = (
        self.messages.GoogleCloudNetworkconnectivityV1betaRejectHubSpokeRequest(
            spokeUri=spoke, details=details
        )
    )
    reject_req = self.messages.NetworkconnectivityProjectsLocationsGlobalHubsRejectSpokeRequest(
        name=hub_ref.RelativeName(),
        googleCloudNetworkconnectivityV1betaRejectHubSpokeRequest=reject_hub_spoke_req,
    )
    return self.hub_service.RejectSpoke(reject_req)

  def QueryHubStatus(
      self,
      hub_ref,
      filter_expression=None,
      group_by='',
      order_by='',
      page_size=100,
      limit=5000,
  ):
    """Call API to query a hub's status in the GA release track."""
    query_hub_status_req = self.messages.NetworkconnectivityProjectsLocationsGlobalHubsQueryStatusRequest(
        name=hub_ref.RelativeName(),
        pageSize=page_size,
        filter=filter_expression,
        orderBy=order_by,
        groupBy=group_by,
    )
    return list_pager.YieldFromList(
        self.hub_service,
        query_hub_status_req,
        field='hubStatusEntries',
        limit=limit,
        batch_size_attribute='pageSize',
        method='QueryStatus',
    )


class GroupsClient(object):
  """Client for group service in network connectivity API."""

  def __init__(self, release_track=base.ReleaseTrack.GA):
    self.release_track = release_track
    self.client = networkconnectivity_util.GetClientInstance(release_track)
    self.messages = networkconnectivity_util.GetMessagesModule(release_track)
    self.group_service = self.client.projects_locations_global_hubs_groups
    self.operation_service = self.client.projects_locations_operations

  def UpdateGroup(self, group_ref, group, update_mask, request_id=None):
    """Call API to update an existing group."""
    name = group_ref.RelativeName()
    update_mask_string = ','.join(update_mask)

    update_req = self.messages.NetworkconnectivityProjectsLocationsGlobalHubsGroupsPatchRequest(
        name=name,
        requestId=request_id,
        group=group,
        updateMask=update_mask_string,
    )
    return self.group_service.Patch(update_req)

  def UpdateGroupBeta(self, group_ref, group, update_mask, request_id=None):
    """Call API to update an existing group in the BETA release track."""
    name = group_ref.RelativeName()
    update_mask_string = ','.join(update_mask)

    update_req = self.messages.NetworkconnectivityProjectsLocationsGlobalHubsGroupsPatchRequest(
        name=name,
        requestId=request_id,
        googleCloudNetworkconnectivityV1betaGroup=group,
        updateMask=update_mask_string,
    )
    return self.group_service.Patch(update_req)

  def Get(self, group_ref):
    """Call API to get an existing group."""
    get_req = self.messages.NetworkconnectivityProjectsLocationsGlobalHubsGroupsGetRequest(
        name=group_ref.RelativeName()
    )
    return self.group_service.Get(get_req)
