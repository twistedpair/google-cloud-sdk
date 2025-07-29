# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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

"""Commands for interacting with the Cloud NetApp Files Host Groups API resource."""

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.netapp import constants
from googlecloudsdk.api_lib.netapp import util as netapp_api_util
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core import resources


class HostGroupsClient(object):
  """Wrapper for working with Host Groups in the Cloud NetApp Files API Client."""

  def __init__(self, release_track=base.ReleaseTrack.ALPHA):
    self.release_track = release_track
    if self.release_track == base.ReleaseTrack.ALPHA:
      self._adapter = AlphaHostGroupsAdapter()
    elif self.release_track == base.ReleaseTrack.BETA:
      self._adapter = BetaHostGroupsAdapter()
    else:
      raise ValueError(
          '[{}] is not a valid API version.'.format(
              netapp_api_util.VERSION_MAP[release_track]
          )
      )

  @property
  def client(self):
    return self._adapter.client

  @property
  def messages(self):
    return self._adapter.messages

  def WaitForOperation(self, operation_ref):
    """Waits on the long-running operation until the done field is True.

    Args:
      operation_ref: the operation reference.

    Raises:
      waiter.OperationError: if the operation contains an error.

    Returns:
      the 'response' field of the Operation.
    """
    return waiter.WaitFor(
        waiter.CloudOperationPollerNoResources(
            self.client.projects_locations_operations
        ),
        operation_ref,
        'Waiting for [{0}] to finish'.format(operation_ref.Name()),
    )

  def CreateHostGroup(self, host_group_ref, async_, config):
    """Create a Cloud NetApp Host Group."""
    request = self.messages.NetappProjectsLocationsHostGroupsCreateRequest(
        parent=host_group_ref.Parent().RelativeName(),
        hostGroupId=host_group_ref.Name(),
        hostGroup=config,
    )
    create_op = self.client.projects_locations_hostGroups.Create(request)
    if async_:
      return create_op
    operation_ref = resources.REGISTRY.ParseRelativeName(
        create_op.name, collection=constants.OPERATIONS_COLLECTION
    )
    return self.WaitForOperation(operation_ref)

  def ParseHostGroupConfig(
      self,
      name=None,
      host_group_type=None,
      hosts=None,
      os_type=None,
      description=None,
      labels=None,
  ):
    """Parses the command line arguments for Create Host Group into a config."""
    host_group = self.messages.HostGroup()
    host_group.name = name
    host_group.type = host_group_type
    host_group.hosts = hosts
    host_group.osType = os_type
    host_group.description = description
    host_group.labels = labels
    return host_group

  def ListHostGroups(self, location_ref):
    """List Cloud NetApp Host Groups.

    Args:
      location_ref: The parent location to list Cloud Netapp Host Groups.

    Returns:
      Generator that yields the Cloud Netapp Host Groups.
    """
    request = self.messages.NetappProjectsLocationsHostGroupsListRequest(
        parent=location_ref
    )
    # Check for unreachable locations.
    response = self.client.projects_locations_hostGroups.List(request)
    for location in response.unreachable:
      log.warning('Location {} may be unreachable.'.format(location))
    return list_pager.YieldFromList(
        self.client.projects_locations_hostGroups,
        request,
        field=constants.HOST_GROUP_RESOURCE,
        batch_size_attribute='pageSize',
    )

  def GetHostGroup(self, host_group_ref):
    """Get a Cloud NetApp Host Group."""
    request = self.messages.NetappProjectsLocationsHostGroupsGetRequest(
        name=host_group_ref.RelativeName()
    )
    return self.client.projects_locations_hostGroups.Get(request)

  def DeleteHostGroup(self, host_group_ref, async_):
    """Delete a Cloud NetApp Host Group."""
    request = self.messages.NetappProjectsLocationsHostGroupsDeleteRequest(
        name=host_group_ref.RelativeName()
    )
    delete_op = self.client.projects_locations_hostGroups.Delete(request)
    if async_:
      return delete_op
    operation_ref = resources.REGISTRY.ParseRelativeName(
        delete_op.name, collection=constants.OPERATIONS_COLLECTION
    )
    return self.WaitForOperation(operation_ref)

  def ParseUpdatedHostGroupConfig(
      self,
      host_group_config,
      hosts=None,
      description=None,
      labels=None,
  ):
    """Parses updates into a host group config.

    Args:
      host_group_config: The host group config to update.
      hosts: list of str, new list of hosts, if any.
      description: str, a new description, if any.
      labels: LabelsValue message, the new labels value, if any.

    Returns:
      The host group message.
    """
    if hosts is not None:
      host_group_config.hosts = hosts
    if description is not None:
      host_group_config.description = description
    if labels is not None:
      host_group_config.labels = labels
    return host_group_config

  def UpdateHostGroup(self, host_group_ref, host_group, update_mask, async_):
    """Updates a Cloud NetApp Host Group.

    Args:
      host_group_ref: the reference to the Host Group.
      host_group: Host group config, the updated host group.
      update_mask: str, a comma-separated list of updated fields.
      async_: bool, if False, wait for the operation to complete.

    Returns:
      an Operation or HostGroup message.
    """
    request = self.messages.NetappProjectsLocationsHostGroupsPatchRequest(
        name=host_group_ref.RelativeName(),
        updateMask=update_mask,
        hostGroup=host_group,
    )
    update_op = self.client.projects_locations_hostGroups.Patch(request)
    if async_:
      return update_op
    operation_ref = resources.REGISTRY.ParseRelativeName(
        update_op.name, collection=constants.OPERATIONS_COLLECTION
    )
    return self.WaitForOperation(operation_ref)


class AlphaHostGroupsAdapter(object):
  """Adapter for the Cloud NetApp Files API Host Group resource."""

  def __init__(self):
    self.release_track = base.ReleaseTrack.ALPHA
    self.client = netapp_api_util.GetClientInstance(
        release_track=self.release_track
    )
    self.messages = netapp_api_util.GetMessagesModule(
        release_track=self.release_track
    )


class BetaHostGroupsAdapter(AlphaHostGroupsAdapter):
  """Adapter for the Beta Cloud NetApp Files API Host Group resource."""

  def __init__(self):
    super(BetaHostGroupsAdapter, self).__init__()
    self.release_track = base.ReleaseTrack.BETA
    self.client = netapp_api_util.GetClientInstance(
        release_track=self.release_track
    )
    self.messages = netapp_api_util.GetMessagesModule(
        release_track=self.release_track
    )
