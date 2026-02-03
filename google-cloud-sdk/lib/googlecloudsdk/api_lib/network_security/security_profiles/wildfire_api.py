# -*- coding: utf-8 -*- #
# Copyright 2026 Google LLC. All Rights Reserved.
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
"""API wrapper for `gcloud network-security security-profiles wildfire-analysis` commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.network_security.security_profiles import sp_api

WILDFIRE_ANALYSIS_PROFILE_TYPE = 'WILDFIRE_ANALYSIS'


class Client(sp_api.Client):
  """API client for WildFire Analysis commands."""

  def CreateWildfireAnalysisProfile(
      self,
      sp_id,
      parent,
      description,
      labels,
  ):
    """Calls the Create Security Profile API to create a WildFire Analysis Profile."""
    profile = self.messages.SecurityProfile(
        type=self._ParseSecurityProfileType(WILDFIRE_ANALYSIS_PROFILE_TYPE),
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

  def ListWildfireAnalysisProfiles(self, parent, limit=None, page_size=None):
    """Calls the ListSecurityProfiles API, filtering by type."""
    return [
        profile
        for profile in self.ListSecurityProfiles(parent, limit, page_size)
        if profile.type
        == self._ParseSecurityProfileType(WILDFIRE_ANALYSIS_PROFILE_TYPE)
    ]

  def UpdateWildfireAnalysisProfile(
      self,
      name,
      description=None,
      wildfire_realtime_lookup=None,
      analyze_windows_executables=None,
      analyze_powershell_script_1=None,
      analyze_powershell_script_2=None,
      analyze_elf=None,
      analyze_ms_office=None,
      analyze_shell=None,
      analyze_ooxml=None,
      analyze_macho=None,
  ):
    """Calls the Update Security Profile API to update a WildFire Analysis Profile."""
    profile = self.messages.SecurityProfile()
    update_mask = []
    if description is not None:
      profile.description = description
      update_mask.append('description')

    wf_profile_to_update = False
    wf_profile_kwargs = {}
    if wildfire_realtime_lookup is not None:
      wf_profile_kwargs['wildfireRealtimeLookup'] = wildfire_realtime_lookup
      update_mask.append('wildfire_analysis_profile.wildfire_realtime_lookup')
      wf_profile_to_update = True

    inline_ml_configs = []
    actions = (
        self.messages.WildfireInlineMlSettingsInlineMlConfig.ActionValueValuesEnum
    )
    file_types = (
        self.messages.WildfireInlineMlSettingsInlineMlConfig.FileTypeValueValuesEnum
    )

    if analyze_windows_executables is not None:
      inline_ml_configs.append(
          self.messages.WildfireInlineMlSettingsInlineMlConfig(
              fileType=file_types.WINDOWS_EXECUTABLE,
              action=actions.ENABLE
              if analyze_windows_executables
              else actions.DISABLE,
          )
      )
    if analyze_powershell_script_1 is not None:
      inline_ml_configs.append(
          self.messages.WildfireInlineMlSettingsInlineMlConfig(
              fileType=file_types.POWERSHELL_SCRIPT1,
              action=actions.ENABLE
              if analyze_powershell_script_1
              else actions.DISABLE,
          )
      )
    if analyze_powershell_script_2 is not None:
      inline_ml_configs.append(
          self.messages.WildfireInlineMlSettingsInlineMlConfig(
              fileType=file_types.POWERSHELL_SCRIPT2,
              action=actions.ENABLE
              if analyze_powershell_script_2
              else actions.DISABLE,
          )
      )
    if analyze_elf is not None:
      inline_ml_configs.append(
          self.messages.WildfireInlineMlSettingsInlineMlConfig(
              fileType=file_types.ELF,
              action=actions.ENABLE if analyze_elf else actions.DISABLE,
          )
      )
    if analyze_ms_office is not None:
      inline_ml_configs.append(
          self.messages.WildfireInlineMlSettingsInlineMlConfig(
              fileType=file_types.MS_OFFICE,
              action=actions.ENABLE if analyze_ms_office else actions.DISABLE,
          )
      )
    if analyze_shell is not None:
      inline_ml_configs.append(
          self.messages.WildfireInlineMlSettingsInlineMlConfig(
              fileType=file_types.SHELL,
              action=actions.ENABLE if analyze_shell else actions.DISABLE,
          )
      )
    if analyze_ooxml is not None:
      inline_ml_configs.append(
          self.messages.WildfireInlineMlSettingsInlineMlConfig(
              fileType=file_types.OOXML,
              action=actions.ENABLE if analyze_ooxml else actions.DISABLE,
          )
      )
    if analyze_macho is not None:
      inline_ml_configs.append(
          self.messages.WildfireInlineMlSettingsInlineMlConfig(
              fileType=file_types.MACHO,
              action=actions.ENABLE if analyze_macho else actions.DISABLE,
          )
      )

    if inline_ml_configs:
      wf_profile_kwargs['wildfireInlineMlSetting'] = (
          self.messages.WildfireInlineMlSettings(
              inlineMlConfigs=inline_ml_configs
          )
      )
      update_mask.append(
          'wildfire_analysis_profile.wildfire_inline_ml_setting'
      )
      wf_profile_to_update = True

    if wf_profile_to_update:
      profile.wildfireAnalysisProfile = self.messages.WildfireAnalysisProfile(
          **wf_profile_kwargs
      )

    request = self.messages.NetworksecurityOrganizationsLocationsSecurityProfilesPatchRequest(
        name=name,
        securityProfile=profile,
        updateMask=','.join(update_mask),
    )
    return self._security_profile_client.Patch(request)
