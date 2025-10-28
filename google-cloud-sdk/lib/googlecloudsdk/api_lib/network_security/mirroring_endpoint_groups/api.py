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
"""API wrapper for `gcloud network-security mirroring-endpoint-groups` commands."""

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

_PACKET_BROKER_SUPPORTED = (base.ReleaseTrack.ALPHA,)


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
  """API client for Mirroring Endpoint Groups commands.

  Attributes:
    messages: API messages class, The Mirroring Endpoint Groups API messages.
  """

  def __init__(self, release_track):
    self._release_track = release_track
    self._client = GetClientInstance(release_track)
    self._endpoint_group_client = (
        self._client.projects_locations_mirroringEndpointGroups
    )
    self._operations_client = self._client.projects_locations_operations
    self.messages = GetMessagesModule(release_track)
    self._resource_parser = resources.Registry()
    self._resource_parser.RegisterApiByName(
        _API_NAME, GetApiVersion(release_track)
    )

  def CreateEndpointGroup(
      self,
      endpoint_group_id,
      parent,
      deployment_groups,
      description,
      endpoint_group_type='DIRECT',
      labels=None,
  ):
    """Calls the CreateEndpointGroup API.

    Args:
      endpoint_group_id: The ID of the Endpoint Group to create.
      parent: The parent of the Endpoint Group to create.
      deployment_groups: The Mirroring Deployment Group(s) to associate with the
        Endpoint Group. Can be a single string or a list of strings.
      description: Description of the Endpoint Group.
      endpoint_group_type: Type of the Endpoint Group (DIRECT or BROKER).
      labels: Labels to apply to the Endpoint Group.

    Returns:
      Operation ref to track the long-running process.
    """

    endpoint_group = self.messages.MirroringEndpointGroup(
        labels=labels,
        description=description,
    )

    if self._release_track in _PACKET_BROKER_SUPPORTED:
      if not endpoint_group_type:
        endpoint_group_type = 'DIRECT'

      endpoint_group.type = (
          self.messages.MirroringEndpointGroup.TypeValueValuesEnum(
              endpoint_group_type
          )
      )
      if endpoint_group_type == 'BROKER':
        if isinstance(deployment_groups, list):
          endpoint_group.mirroringDeploymentGroups = deployment_groups
        else:
          endpoint_group.mirroringDeploymentGroups = [deployment_groups]
      elif endpoint_group_type == 'DIRECT':
        endpoint_group.mirroringDeploymentGroup = deployment_groups
      else:
        raise ValueError(
            f'Unsupported endpoint group type: {endpoint_group_type}'
        )
    else:
      endpoint_group.mirroringDeploymentGroup = deployment_groups

    create_request = self.messages.NetworksecurityProjectsLocationsMirroringEndpointGroupsCreateRequest(
        mirroringEndpointGroup=endpoint_group,
        mirroringEndpointGroupId=endpoint_group_id,
        parent=parent,
    )
    return self._endpoint_group_client.Create(create_request)

  def DeleteEndpointGroup(self, name):
    """Calls the DeleteEndpointGroup API."""
    delete_request = self.messages.NetworksecurityProjectsLocationsMirroringEndpointGroupsDeleteRequest(
        name=name
    )
    return self._endpoint_group_client.Delete(delete_request)

  def UpdateEndpointGroup(self, name, description, update_fields):
    """Calls the UpdateEndpointGroup API.

    Args:
      name: The name of the Endpoint Group to update.
      description: Description of the Endpoint Group.
      update_fields: A dictionary of the fields to update mapped to their new
        values.

    Returns:
      Operation ref to track the long-running process.
    """
    endpoint_group = self.messages.MirroringEndpointGroup(
        labels=update_fields.get('labels', None),
        description=description,
    )

    update_request = self.messages.NetworksecurityProjectsLocationsMirroringEndpointGroupsPatchRequest(
        name=name,
        mirroringEndpointGroup=endpoint_group,
        updateMask=','.join(update_fields.keys()),
    )
    return self._endpoint_group_client.Patch(update_request)

  def DescribeEndpointGroup(self, name):
    """Calls the GetEndpointGroup API."""
    get_request = self.messages.NetworksecurityProjectsLocationsMirroringEndpointGroupsGetRequest(
        name=name
    )
    return self._endpoint_group_client.Get(get_request)

  def ListEndpointGroups(
      self, parent, limit=None, page_size=None, list_filter=None
  ):
    """Calls the ListEndpointGroups API."""
    list_request = self.messages.NetworksecurityProjectsLocationsMirroringEndpointGroupsListRequest(
        parent=parent, filter=list_filter
    )
    return list_pager.YieldFromList(
        self._endpoint_group_client,
        list_request,
        batch_size=page_size,
        limit=limit,
        field='mirroringEndpointGroups',
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

    Polls the Network Security Operation service until the operation completes,
    fails, or max_wait_seconds elapses.

    Args:
      operation_ref: A Resource created by GetOperationRef describing the
        Operation.
      message: The message to display to the user while they wait.
      has_result: If True, the function will return the target of the operation
        (the Mirroring Endpoint Group) when it completes. If False, nothing will
        be returned (useful for Delete operations)
      max_wait: The time to wait for the operation to succeed before timing out.

    Returns:
      if has_result = True, an Endpoint Group entity.
      Otherwise, None.
    """
    if has_result:
      poller = waiter.CloudOperationPoller(
          self._endpoint_group_client, self._operations_client
      )
    else:
      poller = waiter.CloudOperationPollerNoResources(self._operations_client)

    return waiter.WaitFor(
        poller,
        operation_ref,
        message,
        max_wait_ms=int(max_wait.total_seconds()) * 1000,
    )
