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
"""API wrapper for `gcloud network-security mirroring-deployment-groups` commands."""

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
  """API client for Mirroring Deployment Groups commands.

  Attributes:
    messages: API messages class, The Mirroring Deployment Groups messages.
  """

  def __init__(self, release_track):
    self._client = GetClientInstance(release_track)
    self._deployment_group_client = (
        self._client.projects_locations_mirroringDeploymentGroups
    )
    self._operations_client = self._client.projects_locations_operations
    self.messages = GetMessagesModule(release_track)
    self._resource_parser = resources.Registry()
    self._resource_parser.RegisterApiByName(
        _API_NAME, GetApiVersion(release_track)
    )

  def CreateDeploymentGroup(
      self,
      deployment_group_id: str,
      parent: str,
      network: str,
      description: str,
      labels=None,
  ):
    """Calls the CreateDeploymentGroup API.

    Args:
      deployment_group_id: str, the id of the mirroring deployment group.
      parent: str, the parent resource name.
      network: str, the network used for all group deployments.
      description: str, the description of the mirroring deployment group.
      labels: LabelsValue, optional labels as key-value pairs.

    Returns:
      Operation ref to track the long-running process.
    """
    deployment_group = self.messages.MirroringDeploymentGroup(
        labels=labels,
        network=network,
        description=description,
    )

    create_request = self.messages.NetworksecurityProjectsLocationsMirroringDeploymentGroupsCreateRequest(
        mirroringDeploymentGroup=deployment_group,
        mirroringDeploymentGroupId=deployment_group_id,
        parent=parent,
    )
    return self._deployment_group_client.Create(create_request)

  def DeleteDeploymentGroup(self, name):
    """Calls the DeleteDeploymentGroup API.

    Args:
      name: str, the name of the mirroring deployment group.

    Returns:
      Operation ref to track the long-running process.
    """
    delete_request = self.messages.NetworksecurityProjectsLocationsMirroringDeploymentGroupsDeleteRequest(
        name=name
    )
    return self._deployment_group_client.Delete(delete_request)

  def UpdateDeploymentGroup(
      self,
      name,
      description,
      update_fields,
  ):
    """Calls the UpdateDeploymentGroup API.

    Args:
      name: str, the name of the mirroring deployment group.
      description: str, the description of the mirroring deployment group.
      update_fields: A dictionary of fields to update mapped to their new
        values.

    Returns:
      Operation ref to track the long-running process.
    """
    dg = self.messages.MirroringDeploymentGroup(
        labels=update_fields.get('labels', None),
        description=description,
    )

    update_request = self.messages.NetworksecurityProjectsLocationsMirroringDeploymentGroupsPatchRequest(
        name=name,
        mirroringDeploymentGroup=dg,
        updateMask=','.join(update_fields.keys()),
    )
    return self._deployment_group_client.Patch(update_request)

  def DescribeDeploymentGroup(self, name):
    """Calls the GetDeploymentGroup API.

    Args:
      name: str, the name of the mirroring deployment group.

    Returns:
      The mirroring deployment group object.
    """
    get_request = self.messages.NetworksecurityProjectsLocationsMirroringDeploymentGroupsGetRequest(
        name=name
    )
    return self._deployment_group_client.Get(get_request)

  def ListDeploymentGroups(
      self, parent, limit=None, page_size=None, list_filter=None
  ):
    """Calls the ListDeploymentGroups API.

    Args:
      parent: str, the parent resource name.
      limit: int, optional limit for the number of results.
      page_size: int, optional page size for the results.
      list_filter: str, optional filter for the results.

    Returns:
      A generator yielding mirroring deployment groups.
    """
    list_request = self.messages.NetworksecurityProjectsLocationsMirroringDeploymentGroupsListRequest(
        parent=parent, filter=list_filter
    )
    return list_pager.YieldFromList(
        self._deployment_group_client,
        list_request,
        batch_size=page_size,
        limit=limit,
        field='mirroringDeploymentGroups',
        batch_size_attribute='pageSize',
    )

  def GetOperationRef(self, operation):
    """Converts an Operation to a Resource that can be used with `waiter.WaitFor`.

    Args:
      operation: The operation object.

    Returns:
      A Resource describing the operation.
    """
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

    Polls the Firewall Plus Operation service until the operation completes,
    fails, or max_wait_seconds elapses.

    Args:
      operation_ref: A Resource created by GetOperationRef describing the
        operation.
      message: str, the message to display to the user while they wait.
      has_result: bool, if True, returns the target of the operation when it
        completes.
      max_wait: datetime.timedelta, the maximum time to wait for the operation
        to succeed.

    Returns:
      if has_result = True, a MirroringDeploymentGroup entity. Otherwise, None.
    """
    if has_result:
      poller = waiter.CloudOperationPoller(
          self._deployment_group_client, self._operations_client
      )
    else:
      poller = waiter.CloudOperationPollerNoResources(self._operations_client)

    return waiter.WaitFor(
        poller,
        operation_ref,
        message,
        max_wait_ms=int(max_wait.total_seconds()) * 1000,
    )
