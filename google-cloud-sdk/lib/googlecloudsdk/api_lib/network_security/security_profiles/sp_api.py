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
"""API wrapper for `gcloud network-security security-profiles` commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc
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


def GetMessagesModule(release_track=base.ReleaseTrack.GA):
  api_version = GetApiVersion(release_track)
  return apis.GetMessagesModule(_API_NAME, api_version)


def GetClientInstance(release_track=base.ReleaseTrack.GA):
  api_version = GetApiVersion(release_track)
  return apis.GetClientInstance(_API_NAME, api_version)


def GetApiBaseUrl(release_track=base.ReleaseTrack.GA):
  api_version = GetApiVersion(release_track)
  return resources.GetApiBaseUrlOrThrow(_API_NAME, api_version)


def GetApiVersion(release_track=base.ReleaseTrack.GA):
  return _API_VERSION_FOR_TRACK.get(release_track)


def GetEffectiveApiEndpoint(release_track=base.ReleaseTrack.ALPHA):
  api_version = GetApiVersion(release_track)
  return apis.GetEffectiveApiEndpoint(_API_NAME, api_version)


class Client(abc.ABC):
  """API client for all security profile commands."""

  def __init__(self, release_track):
    self._client = GetClientInstance(release_track)
    self._security_profile_client = (
        self._client.organizations_locations_securityProfiles
    )
    self._operations_client = self._client.organizations_locations_operations
    self._locations_client = self._client.organizations_locations
    self.messages = GetMessagesModule(release_track)
    self._resource_parser = resources.Registry()
    self.api_version = _API_VERSION_FOR_TRACK.get(release_track)
    self._resource_parser.RegisterApiByName(
        _API_NAME, _API_VERSION_FOR_TRACK.get(release_track)
    )

  def _ParseSecurityProfileType(self, profile_type):
    return self.messages.SecurityProfile.TypeValueValuesEnum.lookup_by_name(
        profile_type
    )

  def GetSecurityProfile(self, name):
    """Calls the Security Profile Get API to return the security profile object.

    Args:
      name: Fully specified Security Profile.

    Returns:
      Security Profile object.
    """
    api_request = self.messages.NetworksecurityOrganizationsLocationsSecurityProfilesGetRequest(
        name=name
    )
    return self._security_profile_client.Get(api_request)

  def GetOperationsRef(self, operation):
    """Operations to Resource used for `waiter.WaitFor`."""
    return self._resource_parser.ParseRelativeName(
        operation.name,
        'networksecurity.organizations.locations.operations',
        False,
        self.api_version,
    )

  def WaitForOperation(
      self,
      operation_ref,
      message,
      has_result=False,
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
        when it completes. If False, nothing will be returned.
      max_wait: The time to wait for the operation to succeed before timing out.

    Returns:
      if has_result = True, a Security Profile entity.
      Otherwise, None.
    """
    if has_result:
      poller = waiter.CloudOperationPoller(
          self._security_profile_client, self._operations_client
      )
    else:
      poller = waiter.CloudOperationPollerNoResources(self._operations_client)

    response = waiter.WaitFor(
        poller, operation_ref, message, max_wait_ms=max_wait.seconds * 1000
    )

    return response

  def ListSecurityProfiles(
      self,
      parent,
      limit=None,
      page_size=None,
  ):
    """Calls the ListSecurityProfiles API."""
    list_request = self.messages.NetworksecurityOrganizationsLocationsSecurityProfilesListRequest(
        parent=parent
    )
    return list_pager.YieldFromList(
        self._security_profile_client,
        list_request,
        batch_size=page_size,
        limit=limit,
        field='securityProfiles',
        batch_size_attribute='pageSize',
    )

  def UpdateSecurityProfile(self, name, description=None, labels=None):
    """Calls the Update Security Profile API to update a Security Profile.

    Args:
      name: The name of the Security Profile, e.g.
        "organizations/123/locations/global/securityProfiles/my-profile".
      description: The user-specified description of the Security Profile.
      labels: The labels of the Security Profile.

    Returns:
      Updated Security Profile object.
    """
    updated_sp = self.messages.SecurityProfile()
    update_mask = []
    if description:
      updated_sp.description = description
      update_mask.append('description')
    if labels:
      updated_sp.labels = labels
      update_mask.append('labels')

    api_request = self.messages.NetworksecurityOrganizationsLocationsSecurityProfilesPatchRequest(
        name=name,
        securityProfile=updated_sp,
        updateMask=','.join(update_mask),
    )
    return self._security_profile_client.Patch(api_request)
