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
"""API wrapper for `gcloud network-security security-profiles custom-mirroring` commands."""

from __future__ import absolute_import
from __future__ import annotations
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.network_security.security_profiles import sp_api

CUSTOM_MIRRORING_PROFILE_TYPE = 'CUSTOM_MIRRORING'


class Client(sp_api.Client):
  """API client for custom mirroring commands."""

  def GetCustomMirroringProfile(self, name):
    """Calls the Security Profile Get API to return the Mirroring Profile.

    Args:
      name: Fully specified Security Profile.

    Returns:
      An etag and a CustomMirroringProfile object,
      or etag,None if the profile is not a Threat Prevention Profile.
    """

    response = self.GetSecurityProfile(name)
    if response.type != self._ParseSecurityProfileType(
        CUSTOM_MIRRORING_PROFILE_TYPE
    ):
      return response.etag, None

    return response.etag, response.customMirroringProfile

  def ListCustomMirroringProfiles(self, parent, limit=None, page_size=None):
    """Calls the ListSecurityProfiles API, filtering by type."""
    profiles = self.ListSecurityProfiles(parent, limit, page_size)
    return [
        profile
        for profile in profiles
        if profile.type
        == self._ParseSecurityProfileType(CUSTOM_MIRRORING_PROFILE_TYPE)
    ]

  def CreateCustomMirroringProfile(
      self,
      sp_id,
      parent,
      description,
      labels,
      mirroring_endpoint_group,
      mirroring_deployment_groups,
  ):
    """Calls the Create Security Profile API to create a Custom Mirroring Profile."""
    profile = self.messages.SecurityProfile(
        type=self._ParseSecurityProfileType(CUSTOM_MIRRORING_PROFILE_TYPE),
        customMirroringProfile=self.messages.CustomMirroringProfile(
            mirroringEndpointGroup=mirroring_endpoint_group
        ),
        description=description,
        labels=labels,
    )
    # TODO(b/439516438) - remove hasattr check and move into main instantiation
    # above once all API versions have the field.
    if hasattr(profile.customMirroringProfile, 'mirroringDeploymentGroups'):
      profile.customMirroringProfile.mirroringDeploymentGroups = (
          mirroring_deployment_groups or []
      )

    return self._security_profile_client.Create(
        self._create_request(
            parent=parent,
            securityProfile=profile,
            securityProfileId=sp_id,
        )
    )

  def UpdateCustomMirroringProfile(
      self,
      name,
      description: str | None = None,
      labels: dict[str, str] | None = None,
      deployment_groups: list[str] | None = None,
  ):
    """Calls the Update Security Profile API to update a Custom Mirroring Profile.

    Args:
      name: The name of the Security Profile, e.g.
        "organizations/123/locations/global/securityProfiles/my-profile".
      description: The user-specified description of the Security Profile. None
        = no change.
      labels: The labels of the Security Profile. None = no change.
      deployment_groups: The list of deployment groups associated with the
        profile. None = no change.

    Returns:
      Updated Security Profile object.
    """
    updated_sp = self.messages.SecurityProfile(
        customMirroringProfile=self.messages.CustomMirroringProfile()
    )
    update_mask = []
    if description:
      updated_sp.description = description
      update_mask.append('description')
    if labels:
      updated_sp.labels = labels
      update_mask.append('labels')
    if deployment_groups:
      # TODO(b/439516438) - remove hasattr check and move into main
      # instantiation above once all API versions have the field.
      if hasattr(
          updated_sp.customMirroringProfile, 'mirroringDeploymentGroups'
      ):
        updated_sp.customMirroringProfile.mirroringDeploymentGroups = (
            deployment_groups
        )

      update_mask.append('customMirroringProfile.mirroringDeploymentGroups')

    api_request = self._patch_request(
        name=name,
        securityProfile=updated_sp,
        updateMask=','.join(update_mask),
    )
    return self._security_profile_client.Patch(api_request)
