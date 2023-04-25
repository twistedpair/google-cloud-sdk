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
"""API wrapper for `gcloud network-security security-profiles threat-prevention` commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import encoding
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base
from googlecloudsdk.core import resources


API_VERSION_FOR_TRACK = {
    base.ReleaseTrack.ALPHA: 'v1alpha1',
    base.ReleaseTrack.BETA: 'v1beta1',
    base.ReleaseTrack.GA: 'v1',
}
API_NAME = 'networksecurity'


def GetMessagesModule(release_track=base.ReleaseTrack.ALPHA):
  api_version = API_VERSION_FOR_TRACK.get(release_track)
  return apis.GetMessagesModule(API_NAME, api_version)


def GetClientInstance(release_track=base.ReleaseTrack.ALPHA):
  api_version = API_VERSION_FOR_TRACK.get(release_track)
  return apis.GetClientInstance(API_NAME, api_version)


def GetApiBaseUrl(release_track=base.ReleaseTrack.ALPHA):
  api_version = API_VERSION_FOR_TRACK.get(release_track)
  return resources.GetApiBaseUrlOrThrow(API_NAME, api_version)


class Client:
  """API client for threat prevention commands."""

  def __init__(self, release_track):
    self._client = GetClientInstance(release_track)
    self._sp_client = self._client.organizations_locations_securityProfiles
    self._locations_client = self._client.organizations_locations
    self.messages = GetMessagesModule(release_track)
    self._resource_parser = resources.Registry()
    self._resource_parser.RegisterApiByName(
        API_NAME, API_VERSION_FOR_TRACK.get(release_track)
    )

  def _ParseSecurityProfileType(self, profile_type):
    return self.messages.SecurityProfile.TypeValueValuesEnum.lookup_by_name(
        profile_type
    )

  def GetSecurityProfileEntities(self, name):
    """Calls the Security Profile Get API to return the threat prevention profile object.

    Args:
      name: Fully specified Security Profile.

    Returns:
      An etag and a Dict of existing Threat Prevention Profile configuration.
    """
    req = self.messages.NetworksecurityOrganizationsLocationsSecurityProfilesGetRequest(
        name=name
    )
    response = self._sp_client.Get(req)
    if response.threatPreventionProfile is None:
      return response.etag, {
          'severityOverrides': [],
          'threatOverrides': [],
      }
    else:
      profile = encoding.MessageToDict(response.threatPreventionProfile)

      # If Threat Prevention Profile is empty, format the profile response.
      if not any(profile):
        return response.etag, {
            'severityOverrides': [],
            'threatOverrides': [],
        }
      else:
        return response.etag, profile

  def CheckOverridesExist(
      self,
      existing_threat_prevention_profile_object,
      update_mask,
      override,
  ):
    """Checks if override exists in the current threat prevention object.

    Args:
      existing_threat_prevention_profile_object: Existing Threat Prevention
        Profile JSON object.
      update_mask: String Arg specifying type of override which needs update.
      override: The override object provided from the command line.

    Returns:
      A bool specifying if the override exists and index of the override in
      existing_threat_prevention_profile_object if the override exists or None
      is returned.
    """
    update_field = ''

    if update_mask == 'severityOverrides':
      update_field = 'severity'
    elif update_mask == 'threatOverrides':
      update_field = 'threatId'

    for i in range(
        0, len(existing_threat_prevention_profile_object.get(update_mask))
    ):
      if existing_threat_prevention_profile_object.get(update_mask)[i].get(
          update_field
      ) == override.get(update_field):
        return True, i
    return False, None

  def UpdateThreatPreventionProfile(
      self,
      existing_threat_prevention_profile_object,
      overrides,
      update_mask,
      operation_type,
  ):
    """Updates the existing threat_prevention_profile object.

    Args:
      existing_threat_prevention_profile_object: Existing Threat Prevention
        Profile JSON object.
      overrides: JSON object of overrides specifed in command line.
      update_mask: String Arg specifying type of override which needs update.
      operation_type: String Arg specifying the type of operation which is
        performed in this method.

    Returns:
      Modified Threat Prevention Profile JSON object.
    """
    if operation_type == 'add_override':
      for override in overrides:
        does_override_exist, override_index = self.CheckOverridesExist(
            existing_threat_prevention_profile_object, update_mask, override
        )
        if not does_override_exist:
          existing_threat_prevention_profile_object.get(update_mask).extend(
              [override]
          )
      return existing_threat_prevention_profile_object
    elif operation_type == 'update_override':
      for override in overrides:
        does_override_exist, override_index = self.CheckOverridesExist(
            existing_threat_prevention_profile_object, update_mask, override
        )
        if does_override_exist:
          existing_threat_prevention_profile_object.get(update_mask).pop(
              override_index
          )
          existing_threat_prevention_profile_object.get(update_mask).extend(
              [override]
          )
      return existing_threat_prevention_profile_object

  def ModifyOverride(
      self,
      name,
      overrides,
      operation_type,
      update_mask,
      profile_type='THREAT_PREVENTION',
  ):
    """Modify the existing threat prevention profile."""
    etag, existing_threat_prevention_profile_object = (
        self.GetSecurityProfileEntities(name)
    )

    updated_threat_prevention_profile_object = (
        self.UpdateThreatPreventionProfile(
            existing_threat_prevention_profile_object,
            overrides,
            update_mask,
            operation_type,
        )
    )

    if (
        updated_threat_prevention_profile_object
        == existing_threat_prevention_profile_object
    ):
      update_mask = '*'
    else:
      update_mask = 'threatPreventionProfile'

    # Calls the Security Profile Update API
    # to add/update override to threat prevention profile object.
    security_profile = self.messages.SecurityProfile(
        name=name,
        threatPreventionProfile=encoding.DictToMessage(
            updated_threat_prevention_profile_object,
            self.messages.ThreatPreventionProfile,
        ),
        etag=etag,
        type=self._ParseSecurityProfileType(profile_type),
    )
    req = self.messages.NetworksecurityOrganizationsLocationsSecurityProfilesPatchRequest(
        name=name,
        securityProfile=security_profile,
        updateMask=update_mask,
    )
    return self._sp_client.Patch(req)

  def ListOverrides(self, name):
    """Calls the Security Profile Get API to list all Security Profile Overrides."""
    req = self.messages.NetworksecurityOrganizationsLocationsSecurityProfilesGetRequest(
        name=name
    )
    return self._sp_client.Get(req)

  def DeleteOverride(
      self, name, overrides, update_mask, profile_type='THREAT_PREVENTION'
  ):
    """Delete the existing threat prevention profile override."""
    etag, existing_threat_prevention_profile_object = (
        self.GetSecurityProfileEntities(name)
    )

    if update_mask in existing_threat_prevention_profile_object:
      update_field = ''

      if update_mask == 'severityOverrides':
        update_field = 'severity'
      elif update_mask == 'threatOverrides':
        update_field = 'threatId'

      for specified_override in overrides:
        for i in range(
            0, len(existing_threat_prevention_profile_object.get(update_mask))
        ):
          if (
              existing_threat_prevention_profile_object.get(update_mask)[i].get(
                  update_field
              )
              == specified_override
          ):
            existing_threat_prevention_profile_object.get(update_mask).pop(i)
            break

    # Calls the Security Profile Update API
    # to delete override of threat prevention profile object.
    security_profile = self.messages.SecurityProfile(
        name=name,
        threatPreventionProfile=encoding.DictToMessage(
            existing_threat_prevention_profile_object,
            self.messages.ThreatPreventionProfile,
        ),
        etag=etag,
        type=self._ParseSecurityProfileType(profile_type),
    )
    req = self.messages.NetworksecurityOrganizationsLocationsSecurityProfilesPatchRequest(
        name=name,
        securityProfile=security_profile,
        updateMask='threatPreventionProfile',
    )
    return self._sp_client.Patch(req)

  def CreateSecurityProfile(
      self, name, sp_id, parent, description, profile_type='THREAT_PREVENTION'
  ):
    """Calls the Create Security Profile API."""
    security_profile = self.messages.SecurityProfile(
        name=name,
        description=description,
        type=self._ParseSecurityProfileType(profile_type),
    )

    req = self.messages.NetworksecurityOrganizationsLocationsSecurityProfilesCreateRequest(
        parent=parent, securityProfile=security_profile, securityProfileId=sp_id
    )
    return self._sp_client.Create(req)
