# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""API wrapper for `gcloud network-security firewall-endpoints` commands."""

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


def GetEffectiveApiEndpoint(release_track=base.ReleaseTrack.GA):
  api_version = _API_VERSION_FOR_TRACK.get(release_track)
  return apis.GetEffectiveApiEndpoint(_API_NAME, api_version)


def GetApiBaseUrl(release_track=base.ReleaseTrack.GA):
  api_version = _API_VERSION_FOR_TRACK.get(release_track)
  return resources.GetApiBaseUrlOrThrow(_API_NAME, api_version)


def GetApiVersion(release_track=base.ReleaseTrack.GA):
  return _API_VERSION_FOR_TRACK.get(release_track)


class Client:
  """API client for FWP activation commands.

  Attributes:
    release_track: The release track of the API.
    messages: API messages class, The Firewall Plus API messages.
  """

  def __init__(self, release_track, project_scope=False):
    self.release_track = release_track
    self._client = GetClientInstance(release_track)
    self.messages = GetMessagesModule(release_track)
    self._resource_parser = resources.Registry()
    self._resource_parser.RegisterApiByName(
        'networksecurity', _API_VERSION_FOR_TRACK.get(release_track)
    )

    if project_scope:
      self._endpoint_client = self._client.projects_locations_firewallEndpoints
      self._operations_client = self._client.projects_locations_operations
      self._operations_collection = PROJECT_OPERATIONS_COLLECTION
      self._create_request = (
          self.messages.NetworksecurityProjectsLocationsFirewallEndpointsCreateRequest
      )
      self._patch_request = (
          self.messages.NetworksecurityProjectsLocationsFirewallEndpointsPatchRequest
      )
      self._delete_request = (
          self.messages.NetworksecurityProjectsLocationsFirewallEndpointsDeleteRequest
      )
      self._get_request = (
          self.messages.NetworksecurityProjectsLocationsFirewallEndpointsGetRequest
      )
      self._list_request = (
          self.messages.NetworksecurityProjectsLocationsFirewallEndpointsListRequest
      )
    else:
      self._endpoint_client = (
          self._client.organizations_locations_firewallEndpoints
      )
      self._operations_client = self._client.organizations_locations_operations
      self._operations_collection = ORG_OPERATIONS_COLLECTION
      self._create_request = (
          self.messages.NetworksecurityOrganizationsLocationsFirewallEndpointsCreateRequest
      )
      self._patch_request = (
          self.messages.NetworksecurityOrganizationsLocationsFirewallEndpointsPatchRequest
      )
      self._delete_request = (
          self.messages.NetworksecurityOrganizationsLocationsFirewallEndpointsDeleteRequest
      )
      self._get_request = (
          self.messages.NetworksecurityOrganizationsLocationsFirewallEndpointsGetRequest
      )
      self._list_request = (
          self.messages.NetworksecurityOrganizationsLocationsFirewallEndpointsListRequest
      )

  def _ParseEndpointType(self, endpoint_type):
    if endpoint_type is None:
      return None
    return self.messages.FirewallEndpoint.TypeValueValuesEnum.lookup_by_name(
        endpoint_type
    )

  def _ParseThirdPartyEndpointSettings(self, target_firewall_attachment):
    if target_firewall_attachment is None:
      return None
    return self.messages.ThirdPartyEndpointSettings(
        targetFirewallAttachment=target_firewall_attachment,
    )

  def _ParseEndpointSettings(
      self,
      enable_jumbo_frames=None,
      content_cloud_region=None,
      block_partial_http=None,
  ):
    """Returns FirewallEndpointEndpointSettings message."""
    if self.release_track == base.ReleaseTrack.ALPHA:
      if all(
          arg is None
          for arg in [
              enable_jumbo_frames,
              content_cloud_region,
              block_partial_http,
          ]
      ):
        return None
      region_enum = None
      if content_cloud_region:
        region_enum = self.messages.FirewallEndpointEndpointSettings.ContentCloudRegionValueValuesEnum(
            content_cloud_region
        )
      return self.messages.FirewallEndpointEndpointSettings(
          jumboFramesEnabled=enable_jumbo_frames,
          contentCloudRegion=region_enum,
          httpPartialResponseBlocked=block_partial_http,
      )
    else:
      if enable_jumbo_frames is None:
        return None
      return self.messages.FirewallEndpointEndpointSettings(
          jumboFramesEnabled=enable_jumbo_frames,
      )

  def _ParseWildfireSettings(
      self,
      enabled,
      wildfire_region=None,
      wildfire_lookup_timeout=None,
      wildfire_lookup_action_str=None,
      wildfire_analysis_timeout=None,
      wildfire_analysis_action_str=None,
      enable_wildfire_analysis_logging=None,
  ):
    """Returns a WildfireSettings message."""
    if self.release_track == base.ReleaseTrack.ALPHA:
      rt_action_enum = (
          self.messages.FirewallEndpointWildfireSettings.WildfireRealtimeLookupTimeoutActionValueValuesEnum
      )
      ica_action_enum = (
          self.messages.FirewallEndpointWildfireSettingsWildfireInlineCloudAnalysisSettings.TimeoutActionValueValuesEnum
      )
      ws_region_enum = (
          self.messages.FirewallEndpointWildfireSettings.WildfireRegionValueValuesEnum
      )
      lookup_action = None
      if wildfire_lookup_action_str:
        lookup_action = rt_action_enum(wildfire_lookup_action_str)
      analysis_action = None
      if wildfire_analysis_action_str:
        analysis_action = ica_action_enum(wildfire_analysis_action_str)
      region = None
      if wildfire_region:
        region = ws_region_enum(wildfire_region)
      submission_timeout_logging_disabled = None
      if enable_wildfire_analysis_logging is not None:
        submission_timeout_logging_disabled = (
            not enable_wildfire_analysis_logging
        )
      return self.messages.FirewallEndpointWildfireSettings(
          enabled=enabled,
          wildfireRegion=region,
          wildfireRealtimeLookupDuration=str(wildfire_lookup_timeout)
          if wildfire_lookup_timeout
          else None,
          wildfireRealtimeLookupTimeoutAction=lookup_action,
          wildfireInlineCloudAnalysisSettings=self.messages.FirewallEndpointWildfireSettingsWildfireInlineCloudAnalysisSettings(
              maxAnalysisDuration=str(wildfire_analysis_timeout)
              if wildfire_analysis_timeout
              else None,
              timeoutAction=analysis_action,
              submissionTimeoutLoggingDisabled=submission_timeout_logging_disabled,
          ),
      )
    else:
      rt_action_enum = (
          self.messages.WildfireSettings.WildfireRealtimeLookupTimeoutActionValueValuesEnum
      )
      ica_action_enum = (
          self.messages.WildfireInlineCloudAnalysisSettings.TimeoutActionValueValuesEnum
      )
      lookup_action = None
      if wildfire_lookup_action_str:
        lookup_action = rt_action_enum(wildfire_lookup_action_str)
      analysis_action = None
      if wildfire_analysis_action_str:
        analysis_action = ica_action_enum(wildfire_analysis_action_str)
      return self.messages.WildfireSettings(
          enabled=enabled,
          wildfireRegion=wildfire_region,
          wildfireRealtimeLookupDuration=wildfire_lookup_timeout,
          wildfireRealtimeLookupTimeoutAction=lookup_action,
          wildfireInlineCloudAnalysisSettings=self.messages.WildfireInlineCloudAnalysisSettings(
              maxAnalysisDuration=wildfire_analysis_timeout,
              timeoutAction=analysis_action,
              timeoutLoggingDisabled=enable_wildfire_analysis_logging,
          ),
      )

  def CreateEndpoint(
      self,
      name,
      parent,
      description,
      billing_project_id,
      enable_jumbo_frames,
      endpoint_type=None,
      target_firewall_attachment=None,
      labels=None,
      enable_wildfire=None,
      wildfire_region=None,
      content_cloud_region=None,
      wildfire_lookup_timeout=None,
      wildfire_lookup_action=None,
      wildfire_analysis_timeout=None,
      wildfire_analysis_action=None,
      enable_wildfire_analysis_logging=None,
      block_partial_http=None,
  ):
    """Calls the CreateEndpoint API."""

    third_party_endpoint_settings = self._ParseThirdPartyEndpointSettings(
        target_firewall_attachment
    )
    if endpoint_type is not None:
      endpoint = self.messages.FirewallEndpoint(
          labels=labels,
          type=self._ParseEndpointType(endpoint_type),
          thirdPartyEndpointSettings=third_party_endpoint_settings,
          description=description,
          billingProjectId=billing_project_id,
      )
    else:
      endpoint = self.messages.FirewallEndpoint(
          labels=labels,
          description=description,
          billingProjectId=billing_project_id,
      )
    endpoint_settings = self._ParseEndpointSettings(
        enable_jumbo_frames=enable_jumbo_frames,
        content_cloud_region=content_cloud_region,
        block_partial_http=block_partial_http,
    )
    if endpoint_settings:
      endpoint.endpointSettings = endpoint_settings
    if (
        self.release_track == base.ReleaseTrack.ALPHA
        and enable_wildfire is not None
    ):
      endpoint.wildfireSettings = self._ParseWildfireSettings(
          enabled=enable_wildfire,
          wildfire_region=wildfire_region,
          wildfire_lookup_timeout=wildfire_lookup_timeout,
          wildfire_lookup_action_str=wildfire_lookup_action,
          wildfire_analysis_timeout=wildfire_analysis_timeout,
          wildfire_analysis_action_str=wildfire_analysis_action,
          enable_wildfire_analysis_logging=enable_wildfire_analysis_logging,
      )
    create_request = self._create_request(
        firewallEndpoint=endpoint, firewallEndpointId=name, parent=parent
    )
    return self._endpoint_client.Create(create_request)

  def UpdateEndpoint(
      self, name, description, update_mask, labels=None, billing_project_id=None
  ):
    """Calls the UpdateEndpoint API.

    Args:
      name: str, full name of the firewall endpoint.
      description: str, description of the firewall endpoint.
      update_mask: str, comma separated list of fields to update.
      labels: LabelsValue, labels for the firewall endpoint.
      billing_project_id: str, billing project ID.
    Returns:
      Operation ref to track the long-running process.
    """
    endpoint = self.messages.FirewallEndpoint(
        labels=labels,
        description=description,
        billingProjectId=billing_project_id,
    )
    update_request = self._patch_request(
        name=name,
        firewallEndpoint=endpoint,
        updateMask=update_mask,
    )
    return self._endpoint_client.Patch(update_request)

  def DeleteEndpoint(self, name):
    """Calls the DeleteEndpoint API."""
    delete_request = self._delete_request(name=name)
    return self._endpoint_client.Delete(delete_request)

  def DescribeEndpoint(self, name):
    """Calls the GetEndpoint API."""
    get_request = self._get_request(name=name)
    return self._endpoint_client.Get(get_request)

  def ListEndpoints(self, parent, limit=None, page_size=None, list_filter=None):
    """Calls the ListEndpoints API."""
    list_request = self._list_request(parent=parent, filter=list_filter)
    return list_pager.YieldFromList(
        self._endpoint_client,
        list_request,
        batch_size=page_size,
        limit=limit,
        field='firewallEndpoints',
        batch_size_attribute='pageSize',
    )

  def GetOperationRef(self, operation):
    """Converts an Operation to a Resource that can be used with `waiter.WaitFor`."""
    return self._resource_parser.ParseRelativeName(
        operation.name, self._operations_collection
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
        Operation.
      message: The message to display to the user while they wait.
      has_result: If True, the function will return the target of the operation
        (the Firewall Plus Endpoint) when it completes. If False, nothing will
        be returned (useful for Delete operations)
      max_wait: The time to wait for the operation to succeed before timing out.

    Returns:
      if has_result = True, an Endpoint entity.
      Otherwise, None.
    """
    if has_result:
      poller = waiter.CloudOperationPoller(
          self._endpoint_client, self._operations_client
      )
    else:
      poller = waiter.CloudOperationPollerNoResources(self._operations_client)

    return waiter.WaitFor(
        poller,
        operation_ref,
        message,
        max_wait_ms=int(max_wait.total_seconds()) * 1000,
    )
