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
"""API wrapper for `gcloud network-security security-profiles threat-prevention-profiles` commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import encoding
from googlecloudsdk.api_lib.network_security.security_profiles import sp_api

THREAT_PREVENTION_PROFILE_TYPE = 'THREAT_PREVENTION'


class Client(sp_api.Client):
  """API client for threat prevention commands."""

  def GetThreatPreventionProfile(self, name):
    """Calls the Security Profile Get API to return the TPP Profile.

    Args:
      name: Fully specified Security Profile.

    Returns:
      An etag and a Dict of existing Threat Prevention Profile configuration,
      or etag,None if the profile is not a Threat Prevention Profile.
    """
    response = self.GetSecurityProfile(name)
    if response.type != self._ParseSecurityProfileType(
        THREAT_PREVENTION_PROFILE_TYPE
    ):
      return response.etag, None

    if response.threatPreventionProfile is None:
      return response.etag, {
          'severityOverrides': [],
          'threatOverrides': [],
          'antivirusOverrides': [],
      }

    else:
      profile = encoding.MessageToDict(response.threatPreventionProfile)

      # If Threat Prevention Profile is empty, format the profile response.
      if not any(profile):
        return response.etag, {
            'severityOverrides': [],
            'threatOverrides': [],
            'antivirusOverrides': [],
        }
      else:
        if profile.get('antivirusOverrides') is None:
          profile['antivirusOverrides'] = []
        if profile.get('severityOverrides') is None:
          profile['severityOverrides'] = []
        if profile.get('threatOverrides') is None:
          profile['threatOverrides'] = []

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

    if update_mask == 'antivirusOverrides':
      update_field = 'protocol'
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
      overrides: JSON object of overrides specified in command line.
      update_mask: String Arg specifying type of override which needs update.
      operation_type: String Arg specifying the type of operation which is
        performed in this method.

    Returns:
      Modified Threat Prevention Profile JSON object.
    """
    if operation_type == 'add_override':
      for override in overrides:
        does_override_exist, _ = self.CheckOverridesExist(
            existing_threat_prevention_profile_object,
            update_mask,
            override,
        )
        if not does_override_exist:
          existing_threat_prevention_profile_object.get(update_mask).extend(
              [override]
          )
      return existing_threat_prevention_profile_object
    elif operation_type == 'update_override':
      for override in overrides:
        does_override_exist, override_index = self.CheckOverridesExist(
            existing_threat_prevention_profile_object,
            update_mask,
            override,
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
      profile_type=THREAT_PREVENTION_PROFILE_TYPE,
      labels=None,
  ):
    """Modify the existing threat prevention profile."""
    etag, existing_threat_prevention_profile_object = (
        self.GetThreatPreventionProfile(name)
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
        labels=labels,
    )
    api_request = self._patch_request(
        name=name,
        securityProfile=security_profile,
        updateMask=update_mask,
    )
    return self._security_profile_client.Patch(api_request)

  def ListOverrides(self, name):
    """Calls the Security Profile Get API to list all Security Profile Overrides."""
    api_request = self._get_request(
        name=name
    )
    return self._security_profile_client.Get(api_request)

  def DeleteOverride(
      self,
      name,
      overrides,
      update_mask,
      profile_type=THREAT_PREVENTION_PROFILE_TYPE,
      labels=None,
  ):
    """Delete the existing threat prevention profile override."""
    etag, existing_threat_prevention_profile_object = (
        self.GetThreatPreventionProfile(name)
    )

    if update_mask in existing_threat_prevention_profile_object:
      update_field = ''
      if update_mask == 'antivirusOverrides':
        update_field = 'protocol'
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
        labels=labels,
    )
    api_request = self._patch_request(
        name=name,
        securityProfile=security_profile,
        updateMask='threatPreventionProfile',
    )
    return self._security_profile_client.Patch(api_request)

  def CreateThreatPreventionProfile(
      self,
      name,
      sp_id,
      parent,
      description,
      labels=None,
  ):
    """Calls the SPG API to create a Threat Prevention Profile."""
    profile = self.messages.SecurityProfile(
        name=name,
        type=self._ParseSecurityProfileType(THREAT_PREVENTION_PROFILE_TYPE),
        description=description,
        labels=labels,
    )
    return self._security_profile_client.Create(
        self._create_request(
            parent=parent,
            securityProfile=profile,
            securityProfileId=sp_id,
        )
    )

  def ListThreatPreventionProfiles(self, parent, limit=None, page_size=None):
    """Calls the ListSecurityProfiles API, filtering by type."""
    return [
        profile
        for profile in self.ListSecurityProfiles(parent, limit, page_size)
        if profile.type
        == self._ParseSecurityProfileType(THREAT_PREVENTION_PROFILE_TYPE)
    ]
