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
"""API wrapper for `gcloud network-security security-profiles url-filtering` commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.network_security.security_profiles import sp_api

URL_FILTERING_PROFILE_TYPE = 'URL_FILTERING'


class Client(sp_api.Client):
  """API client for URL filtering commands."""

  def CreateUrlFilteringProfile(
      self,
      sp_id,
      parent,
      description,
      labels,
  ):
    """Calls the Create Security Profile API to create a Url Filtering Profile."""
    profile = self.messages.SecurityProfile(
        type=self._ParseSecurityProfileType(URL_FILTERING_PROFILE_TYPE),
        description=description,
        labels=labels,
    )
    return self._security_profile_client.Create(
        self.messages.NetworksecurityOrganizationsLocationsSecurityProfilesCreateRequest(
            parent=parent,
            securityProfile=profile,
            securityProfileId=sp_id,
        )
    )

  def ListUrlFilteringProfiles(self, parent, limit=None, page_size=None):
    """Calls the ListSecurityProfiles API, filtering by type."""
    profiles = self.ListSecurityProfiles(parent, limit, page_size)
    return [
        profile
        for profile in profiles
        if profile.type
        == self._ParseSecurityProfileType(URL_FILTERING_PROFILE_TYPE)
    ]
