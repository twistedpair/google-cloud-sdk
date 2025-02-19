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
"""API wrapper for `gcloud network-security mirroring-endpoint-group-associations` commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import datetime

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base
from googlecloudsdk.core import resources


_API_VERSION_FOR_TRACK = {
    base.ReleaseTrack.ALPHA: 'v1alpha1',
    base.ReleaseTrack.BETA: 'v1beta1',
    base.ReleaseTrack.GA: 'v1',
}
_API_NAME = 'networksecurity'


def GetMessagesModule(release_track=base.ReleaseTrack.ALPHA):
  api_version = GetApiVersion(release_track)
  return apis.GetMessagesModule(_API_NAME, api_version)


def GetClientInstance(release_track=base.ReleaseTrack.ALPHA):
  api_version = GetApiVersion(release_track)
  return apis.GetClientInstance(_API_NAME, api_version)


def GetEffectiveApiEndpoint(release_track=base.ReleaseTrack.ALPHA):
  api_version = GetApiVersion(release_track)
  return apis.GetEffectiveApiEndpoint(_API_NAME, api_version)


def GetApiVersion(release_track=base.ReleaseTrack.ALPHA):
  return _API_VERSION_FOR_TRACK.get(release_track)


class Client:
  """API client for Mirroring Endpoint Group Association commands.

  Attributes:
    messages: API messages class, The Mirroring Endpoint Group Association API
      messages.
  """

  def __init__(self, release_track):
    self._client = GetClientInstance(release_track)
    self._association_client = (
        self._client.projects_locations_mirroringEndpointGroupAssociations
    )
    self._operations_client = self._client.projects_locations_operations
    self.messages = GetMessagesModule(release_track)
    self._resource_parser = resources.Registry()
    self._resource_parser.RegisterApiByName(
        _API_NAME, GetApiVersion(release_track)
    )

  def CreateEndpointGroupAssociation(
      self,
      association_id,
      parent,
      network,
      mirroring_endpoint_group,
      labels=None,
  ):
    """Calls the CreateEndpointGroupAssociation API."""

    association = self.messages.MirroringEndpointGroupAssociation(
        labels=labels,
        network=network,
        mirroringEndpointGroup=mirroring_endpoint_group,
    )
    create_request = self.messages.NetworksecurityProjectsLocationsMirroringEndpointGroupAssociationsCreateRequest(
        mirroringEndpointGroupAssociation=association,
        mirroringEndpointGroupAssociationId=association_id,
        parent=parent,
    )
    return self._association_client.Create(create_request)

  def DeleteEndpointGroupAssociation(self, name):
    """Calls the DeleteEndpointGroupAssociation API."""
    delete_request = self.messages.NetworksecurityProjectsLocationsMirroringEndpointGroupAssociationsDeleteRequest(
        name=name
    )
    return self._association_client.Delete(delete_request)

  def UpdateEndpointGroupAssociation(
      self,
      name,
      update_fields,
  ):
    """Calls the UpdateEndpointGroupAssociation API."""
    association = self.messages.MirroringEndpointGroupAssociation(
        labels=update_fields.get('labels', None)
    )
    update_request = self.messages.NetworksecurityProjectsLocationsMirroringEndpointGroupAssociationsPatchRequest(
        name=name,
        mirroringEndpointGroupAssociation=association,
        updateMask=','.join(update_fields.keys()),
    )
    return self._association_client.Patch(update_request)

  def DescribeEndpointGroupAssociation(self, name):
    """Calls the GetEndpointGroupAssociation API."""
    get_request = self.messages.NetworksecurityProjectsLocationsMirroringEndpointGroupAssociationsGetRequest(
        name=name
    )
    return self._association_client.Get(get_request)

  def ListEndpointGroupAssociations(
      self, parent, limit=None, page_size=None, list_filter=None
  ):
    """Calls the ListEndpointGroupAssociations API."""
    list_request = self.messages.NetworksecurityProjectsLocationsMirroringEndpointGroupAssociationsListRequest(
        parent=parent, filter=list_filter
    )
    return list_pager.YieldFromList(
        self._association_client,
        list_request,
        batch_size=page_size,
        limit=limit,
        field='mirroringEndpointGroupAssociations',
        batch_size_attribute='pageSize',
    )

  def GetOperationRef(self, operation):
    """Converts an Operation to a Resource that can be used with `waiter.WaitFor`."""
    return self._resource_parser.ParseRelativeName(
        operation.name, 'networksecurity.projects.locations.operations'
    )

  def WaitForOperation(
      self,
      operation_ref,
      message,
      has_result=True,
      max_wait=datetime.timedelta(seconds=600),
  ):
    """Waits for an operation to complete.

    Polls the Mirroring Endpoint Group Association Operation service until the
    operation completes,
    fails, or max_wait_seconds elapses.

    Args:
      operation_ref: A Resource created by GetOperationRef describing the
        Operation.
      message: The message to display to the user while they wait.
      has_result: If True, the function will return the target of the operation
        (the Mirroring Endpoint Group Association) when it completes. If False,
        nothing will be returned (useful for Delete operations)
      max_wait: The time to wait for the operation to succeed before timing out.

    Returns:
      if has_result = True, an Association entity.
      Otherwise, None.
    """
    if has_result:
      poller = waiter.CloudOperationPoller(
          self._association_client, self._operations_client
      )
    else:
      poller = waiter.CloudOperationPollerNoResources(self._operations_client)

    return waiter.WaitFor(
        poller,
        operation_ref,
        message,
        max_wait_ms=int(max_wait.total_seconds()) * 1000,
    )
