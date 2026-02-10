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
"""API wrapper for `gcloud network-security security-profile-groups` commands."""

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
ORG_OPERATIONS_COLLECTION = 'networksecurity.organizations.locations.operations'
PROJECT_OPERATIONS_COLLECTION = 'networksecurity.projects.locations.operations'


def GetMessagesModule(release_track=base.ReleaseTrack.GA):
  api_version = _API_VERSION_FOR_TRACK.get(release_track)
  return apis.GetMessagesModule(_API_NAME, api_version)


def GetClientInstance(release_track=base.ReleaseTrack.GA):
  api_version = _API_VERSION_FOR_TRACK.get(release_track)
  return apis.GetClientInstance(_API_NAME, api_version)


def GetApiBaseUrl(release_track=base.ReleaseTrack.GA):
  api_version = _API_VERSION_FOR_TRACK.get(release_track)
  return resources.GetApiBaseUrlOrThrow(_API_NAME, api_version)


def GetApiVersion(release_track=base.ReleaseTrack.GA):
  return _API_VERSION_FOR_TRACK.get(release_track)


def GetEffectiveApiEndpoint(release_track=base.ReleaseTrack.ALPHA):
  api_version = GetApiVersion(release_track)
  return apis.GetEffectiveApiEndpoint(_API_NAME, api_version)


class Client:
  """API client for security profile group commands."""

  def __init__(self, release_track, project_scope=False):
    self._client = GetClientInstance(release_track)
    self.messages = GetMessagesModule(release_track)
    self._resource_parser = resources.Registry()
    self.api_version = _API_VERSION_FOR_TRACK.get(release_track)
    self._resource_parser.RegisterApiByName(
        _API_NAME, _API_VERSION_FOR_TRACK.get(release_track)
    )

    if project_scope:
      self._security_profile_group_client = (
          self._client.projects_locations_securityProfileGroups
      )
      self._operations_client = self._client.projects_locations_operations
      self._locations_client = self._client.projects_locations
      self._operations_collection = PROJECT_OPERATIONS_COLLECTION
      self._create_request = (
          self.messages.NetworksecurityProjectsLocationsSecurityProfileGroupsCreateRequest
      )
      self._get_request = (
          self.messages.NetworksecurityProjectsLocationsSecurityProfileGroupsGetRequest
      )
      self._list_request = (
          self.messages.NetworksecurityProjectsLocationsSecurityProfileGroupsListRequest
      )
      self._patch_request = (
          self.messages.NetworksecurityProjectsLocationsSecurityProfileGroupsPatchRequest
      )
      self._delete_request = (
          self.messages.NetworksecurityProjectsLocationsSecurityProfileGroupsDeleteRequest
      )
    else:
      self._security_profile_group_client = (
          self._client.organizations_locations_securityProfileGroups
      )
      self._operations_client = self._client.organizations_locations_operations
      self._locations_client = self._client.organizations_locations
      self._operations_collection = ORG_OPERATIONS_COLLECTION
      self._create_request = (
          self.messages.NetworksecurityOrganizationsLocationsSecurityProfileGroupsCreateRequest
      )
      self._get_request = (
          self.messages.NetworksecurityOrganizationsLocationsSecurityProfileGroupsGetRequest
      )
      self._list_request = (
          self.messages.NetworksecurityOrganizationsLocationsSecurityProfileGroupsListRequest
      )
      self._patch_request = (
          self.messages.NetworksecurityOrganizationsLocationsSecurityProfileGroupsPatchRequest
      )
      self._delete_request = (
          self.messages.NetworksecurityOrganizationsLocationsSecurityProfileGroupsDeleteRequest
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
      if has_result = True, a Security Profile Group entity.
      Otherwise, None.
    """
    if has_result:
      poller = waiter.CloudOperationPoller(
          self._security_profile_group_client, self._operations_client
      )
    else:
      poller = waiter.CloudOperationPollerNoResources(self._operations_client)

    response = waiter.WaitFor(
        poller, operation_ref, message, max_wait_ms=max_wait.seconds * 1000
    )

    return response

  def GetOperationsRef(self, operation):
    """Operations to Resource used for `waiter.WaitFor`."""
    return self._resource_parser.ParseRelativeName(
        operation.name,
        self._operations_collection,
        False,
        self.api_version,
    )

  def GetSecurityProfileGroup(self, security_profile_group_name):
    """Calls the Security Profile Group Get API.

    Args:
      security_profile_group_name: Fully specified Security Profile Group.

    Returns:
      Security Profile Group object.
    """
    api_request = self._get_request(name=security_profile_group_name)
    return self._security_profile_group_client.Get(api_request)

  def CreateSecurityProfileGroup(
      self,
      security_profile_group_name,
      security_profile_group_id,
      parent,
      description,
      threat_prevention_profile=None,
      url_filtering_profile=None,
      wildfire_analysis_profile=None,
      custom_mirroring_profile=None,
      custom_intercept_profile=None,
      labels=None,
  ):
    """Calls the Create Security Profile Group API."""
    security_profile_group = self.messages.SecurityProfileGroup(
        name=security_profile_group_name,
        description=description,
        threatPreventionProfile=threat_prevention_profile,
        labels=labels,
    )
    if hasattr(security_profile_group, 'urlFilteringProfile'):
      security_profile_group.urlFilteringProfile = url_filtering_profile
    if hasattr(security_profile_group, 'wildfireAnalysisProfile'):
      security_profile_group.wildfireAnalysisProfile = wildfire_analysis_profile
    # v1 API doesn't have the new field yet, so don't assign it.
    if hasattr(security_profile_group, 'customMirroringProfile'):
      security_profile_group.customMirroringProfile = custom_mirroring_profile
    if hasattr(security_profile_group, 'customInterceptProfile'):
      security_profile_group.customInterceptProfile = custom_intercept_profile

    api_request = self._create_request(
        parent=parent,
        securityProfileGroup=security_profile_group,
        securityProfileGroupId=security_profile_group_id,
    )
    return self._security_profile_group_client.Create(api_request)

  def UpdateSecurityProfileGroup(
      self,
      security_profile_group_name,
      description,
      threat_prevention_profile,
      url_filtering_profile,
      wildfire_analysis_profile,
      update_mask,
      labels=None,
  ):
    """Calls the Patch Security Profile Group API.

    Args:
      security_profile_group_name: The name of the security profile group to
        update.
      description: The description of the security profile group.
      threat_prevention_profile: The threat prevention profile to associate.
      url_filtering_profile: The URL filtering profile to associate.
      wildfire_analysis_profile: The WildFire analysis profile to associate.
      update_mask: A comma-separated string of fields to update.
      labels: A dictionary of user-defined labels for the security profile
        group.

    Returns:
      The operation returned by the Patch API.
    """
    security_profile_group = self.messages.SecurityProfileGroup(
        name=security_profile_group_name,
        description=description,
        threatPreventionProfile=threat_prevention_profile,
        labels=labels,
    )

    if hasattr(security_profile_group, 'urlFilteringProfile'):
      security_profile_group.urlFilteringProfile = url_filtering_profile
    if hasattr(security_profile_group, 'wildfireAnalysisProfile'):
      security_profile_group.wildfireAnalysisProfile = wildfire_analysis_profile

    api_request = self._patch_request(
        name=security_profile_group_name,
        securityProfileGroup=security_profile_group,
        updateMask=update_mask,
    )
    return self._security_profile_group_client.Patch(api_request)

  def DeleteSecurityProfileGroup(
      self,
      security_profile_group_name,
  ):
    """Calls the Delete Security Profile Group API."""
    api_request = self._delete_request(
        name=security_profile_group_name,
    )
    return self._security_profile_group_client.Delete(api_request)

  def ListSecurityProfileGroups(
      self,
      parent,
      limit=None,
      page_size=None,
  ):
    """Calls the ListSecurityProfileGroups API."""
    list_request = self._list_request(
        parent=parent,
    )
    return list_pager.YieldFromList(
        self._security_profile_group_client,
        list_request,
        batch_size=page_size,
        limit=limit,
        field='securityProfileGroups',
        batch_size_attribute='pageSize',
    )
