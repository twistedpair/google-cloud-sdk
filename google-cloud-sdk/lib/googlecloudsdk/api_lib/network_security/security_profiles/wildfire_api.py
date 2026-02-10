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
from googlecloudsdk.core import exceptions

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

  def AddSubmissionRule(self, name, file_type_choices, direction):
    """Adds a submission rule to a WildFire Analysis Profile."""
    sp_to_update = self.GetSecurityProfile(name)
    if sp_to_update is None:
      raise exceptions.Error(f'Security profile [{name}] not found.')
    if sp_to_update.wildfireAnalysisProfile is None:
      raise exceptions.Error(
          f'Security profile [{name}] is not a WildFire Analysis profile.'
      )
    if sp_to_update.wildfireAnalysisProfile.wildfireSubmissionRules is None:
      sp_to_update.wildfireAnalysisProfile.wildfireSubmissionRules = []

    direction_enum = (
        self.messages.WildfireSubmissionRule.DirectionValueValuesEnum(
            direction
        )
    )
    if 'ANY_FILE' in file_type_choices:
      file_selection_mode = (
          self.messages.WildfireSubmissionRule.FileSelectionModeValueValuesEnum.ALL_FILE_TYPES
      )
      custom_file_types = None
    else:
      file_selection_mode = (
          self.messages.WildfireSubmissionRule.FileSelectionModeValueValuesEnum.CUSTOM_FILE_TYPES
      )
      custom_file_types = self.messages.WildfireSubmissionRuleCustomFileTypes(
          fileTypes=[
              self.messages.WildfireSubmissionRuleCustomFileTypes.FileTypesValueListEntryValuesEnum(
                  ft
              )
              for ft in file_type_choices
          ]
      )

    new_rule = self.messages.WildfireSubmissionRule(
        direction=direction_enum,
        fileSelectionMode=file_selection_mode,
        customFileTypes=custom_file_types,
    )
    sp_to_update.wildfireAnalysisProfile.wildfireSubmissionRules.append(
        new_rule
    )
    patch_request = self.messages.NetworksecurityOrganizationsLocationsSecurityProfilesPatchRequest(
        name=name,
        securityProfile=sp_to_update,
        updateMask='wildfire_analysis_profile.wildfire_submission_rules',
    )
    return self._security_profile_client.Patch(patch_request)

  def DeleteSubmissionRule(self, name, file_type_choices, direction):
    """Deletes a submission rule from a WildFire Analysis Profile."""
    sp_to_update = self.GetSecurityProfile(name)
    if sp_to_update.wildfireAnalysisProfile is None:
      raise exceptions.Error(
          'Security profile [{}] is not a WildFire Analysis profile.'.format(
              name
          )
      )
    if sp_to_update.wildfireAnalysisProfile.wildfireSubmissionRules is None:
      sp_to_update.wildfireAnalysisProfile.wildfireSubmissionRules = []

    rules = sp_to_update.wildfireAnalysisProfile.wildfireSubmissionRules
    direction_enum = (
        self.messages.WildfireSubmissionRule.DirectionValueValuesEnum(
            direction
        )
    )
    file_selection_mode_enum = (
        self.messages.WildfireSubmissionRule.FileSelectionModeValueValuesEnum
    )
    if 'ANY_FILE' in file_type_choices:
      file_selection_mode = file_selection_mode_enum.ALL_FILE_TYPES
    else:
      file_selection_mode = file_selection_mode_enum.CUSTOM_FILE_TYPES

    # WildFire allow duplicate rules, so we iterate through the list
    # and remove the first matching rule.
    rule_to_remove_index = -1
    for i, rule in enumerate(rules):
      if rule.direction != direction_enum:
        continue
      if rule.fileSelectionMode != file_selection_mode:
        continue
      if file_selection_mode == file_selection_mode_enum.ALL_FILE_TYPES:
        rule_to_remove_index = i
        break
      else:
        if rule.customFileTypes is not None and set(
            str(ft) for ft in rule.customFileTypes.fileTypes
        ) == set(file_type_choices):
          rule_to_remove_index = i
          break

    if rule_to_remove_index != -1:
      rules.pop(rule_to_remove_index)
    else:
      raise sp_api.ResourceNotFoundException(
          'Submission rule with file-types [{0}] and direction [{1}] not'
          ' found in security profile [{2}]'.format(
              ','.join(file_type_choices), direction, name
          )
      )

    patch_request = self.messages.NetworksecurityOrganizationsLocationsSecurityProfilesPatchRequest(
        name=name,
        securityProfile=sp_to_update,
        updateMask='wildfire_analysis_profile.wildfire_submission_rules',
    )
    return self._security_profile_client.Patch(patch_request)

  def AddInlineCloudAnalysisRule(
      self, name, file_types_choices, direction, action
  ):
    """Adds an inline cloud analysis rule to a WildFire Analysis Profile."""
    sp_to_update = self.GetSecurityProfile(name)
    if sp_to_update is None:
      raise exceptions.Error(f'Security profile [{name}] not found.')
    if sp_to_update.wildfireAnalysisProfile is None:
      raise exceptions.Error(
          f'Security profile [{name}] is not a WildFire Analysis profile.'
      )
    if (
        sp_to_update.wildfireAnalysisProfile.wildfireInlineCloudAnalysisRules
        is None
    ):
      sp_to_update.wildfireAnalysisProfile.wildfireInlineCloudAnalysisRules = []

    direction_enum = (
        self.messages.WildfireInlineCloudAnalysisRule.DirectionValueValuesEnum(
            direction
        )
    )
    action_enum = (
        self.messages.WildfireInlineCloudAnalysisRule.ActionValueValuesEnum(
            action
        )
    )
    if 'ANY_FILE' in file_types_choices:
      file_selection_mode = (
          self.messages.WildfireInlineCloudAnalysisRule.FileSelectionModeValueValuesEnum.ALL_FILE_TYPES
      )
      custom_file_types = None
    else:
      file_selection_mode = (
          self.messages.WildfireInlineCloudAnalysisRule.FileSelectionModeValueValuesEnum.CUSTOM_FILE_TYPES
      )
      file_type_enums = [
          self.messages.WildfireInlineCloudAnalysisRuleCustomFileTypes.FileTypesValueListEntryValuesEnum(
              ft
          )
          for ft in file_types_choices
      ]
      custom_file_types = (
          self.messages.WildfireInlineCloudAnalysisRuleCustomFileTypes(
              fileTypes=file_type_enums
          )
      )

    new_rule = self.messages.WildfireInlineCloudAnalysisRule(
        direction=direction_enum,
        action=action_enum,
        fileSelectionMode=file_selection_mode,
        customFileTypes=custom_file_types,
    )
    sp_to_update.wildfireAnalysisProfile.wildfireInlineCloudAnalysisRules.append(
        new_rule
    )
    patch_request = self.messages.NetworksecurityOrganizationsLocationsSecurityProfilesPatchRequest(
        name=name,
        securityProfile=sp_to_update,
        updateMask=(
            'wildfire_analysis_profile.wildfire_inline_cloud_analysis_rules'
        ),
    )
    return self._security_profile_client.Patch(patch_request)

  def DeleteInlineCloudAnalysisRule(
      self, name, file_types_upper, direction, action
  ):
    """Deletes an inline cloud analysis rule from a WildFire Analysis Profile."""
    sp_to_update = self.GetSecurityProfile(name)
    if sp_to_update is None:
      raise exceptions.Error(f'Security profile [{name}] not found.')
    if sp_to_update.wildfireAnalysisProfile is None:
      raise exceptions.Error(
          f'Security profile [{name}] is not a WildFire Analysis profile.'
      )

    rules = (
        sp_to_update.wildfireAnalysisProfile.wildfireInlineCloudAnalysisRules
    )
    if not rules:
      raise exceptions.Error(
          f'Security profile [{name}] has no inline cloud analysis rules to'
          ' delete.'
      )

    direction_enum = (
        self.messages.WildfireInlineCloudAnalysisRule.DirectionValueValuesEnum(
            direction
        )
    )
    action_enum = (
        self.messages.WildfireInlineCloudAnalysisRule.ActionValueValuesEnum(
            action
        )
    )

    if 'ANY_FILE' in file_types_upper:
      file_selection_mode_enum = (
          self.messages.WildfireInlineCloudAnalysisRule.FileSelectionModeValueValuesEnum.ALL_FILE_TYPES
      )
    else:
      file_selection_mode_enum = (
          self.messages.WildfireInlineCloudAnalysisRule.FileSelectionModeValueValuesEnum.CUSTOM_FILE_TYPES
      )

    rule_found = False
    updated_rules = []
    for rule in rules:
      current_rule_matches = False
      if rule.direction == direction_enum and rule.action == action_enum:
        if 'ANY_FILE' in file_types_upper:
          if rule.fileSelectionMode == file_selection_mode_enum:
            current_rule_matches = True
        else:  # custom file types
          if (
              rule.fileSelectionMode == file_selection_mode_enum
              and rule.customFileTypes
              and rule.customFileTypes.fileTypes
          ):
            rule_file_types = sorted(
                str(ft) for ft in rule.customFileTypes.fileTypes
            )
            if rule_file_types == sorted(file_types_upper):
              current_rule_matches = True

      if current_rule_matches and not rule_found:
        rule_found = True
        # don't append to updated_rules to delete it
      else:
        updated_rules.append(rule)

    if not rule_found:
      raise exceptions.Error(
          'No matching inline cloud analysis rule found to delete.'
      )

    sp_to_update.wildfireAnalysisProfile.wildfireInlineCloudAnalysisRules = (
        updated_rules
    )
    patch_request = self.messages.NetworksecurityOrganizationsLocationsSecurityProfilesPatchRequest(
        name=name,
        securityProfile=sp_to_update,
        updateMask=(
            'wildfire_analysis_profile.wildfire_inline_cloud_analysis_rules'
        ),
    )
    return self._security_profile_client.Patch(patch_request)

  def AddInlineMlException(self, name, partial_hash, filename):
    """Adds an inline ml exception to a WildFire Analysis Profile."""
    sp_to_update = self.GetSecurityProfile(name)
    if sp_to_update is None:
      raise exceptions.Error(f'Security profile [{name}] not found.')
    if sp_to_update.wildfireAnalysisProfile is None:
      raise exceptions.Error(
          f'Security profile [{name}] is not a WildFire Analysis profile.'
      )
    if getattr(
        sp_to_update.wildfireAnalysisProfile, 'wildfireInlineMlSetting', None
    ) is None:
      sp_to_update.wildfireAnalysisProfile.wildfireInlineMlSetting = (
          self.messages.WildfireInlineMlSettings()
      )

    if (
        getattr(
            sp_to_update.wildfireAnalysisProfile.wildfireInlineMlSetting,
            'fileExceptions',
            None,
        )
        is None
    ):
      sp_to_update.wildfireAnalysisProfile.wildfireInlineMlSetting.fileExceptions = (
          []
      )

    new_exception = self.messages.WildfireInlineMlFileException(
        partialHash=partial_hash,
        filename=filename,
    )
    sp_to_update.wildfireAnalysisProfile.wildfireInlineMlSetting.fileExceptions.append(
        new_exception
    )
    patch_request = self.messages.NetworksecurityOrganizationsLocationsSecurityProfilesPatchRequest(
        name=name,
        securityProfile=sp_to_update,
        updateMask='wildfire_analysis_profile.wildfire_inline_ml_setting.file_exceptions',
    )
    return self._security_profile_client.Patch(patch_request)

  def AddOverride(
      self,
      name,
      action,
      threat_ids=None,
      wildfire_protocols=None,
      wildfire_inline_ml_protocols=None,
  ):
    """Adds an override to a WildFire Analysis Profile."""
    sp_to_update = self.GetSecurityProfile(name)
    if sp_to_update is None:
      raise exceptions.Error(f'Security profile [{name}] not found.')
    if sp_to_update.wildfireAnalysisProfile is None:
      raise exceptions.Error(
          f'Security profile [{name}] is not a WildFire Analysis profile.'
      )
    # Exactly one of three types of overrides must be specified,
    # and they're mutually exclusive.
    update_mask = ''
    action_str = (
        'WILDFIRE_' + action
        if action != 'DEFAULT'
        else 'WILDFIRE_DEFAULT_ACTION'
    )
    # --threat_ids modifies WildfireThreatOverride.
    if threat_ids:
      # Allow multiple threat_ids, and remove duplicates.
      threat_ids = sorted(set(threat_ids))
      action_enum = self.messages.WildfireThreatOverride.ActionValueValuesEnum(
          action_str
      )
      if sp_to_update.wildfireAnalysisProfile.wildfireThreatOverrides is None:
        sp_to_update.wildfireAnalysisProfile.wildfireThreatOverrides = []
      # New provided threat_id may conflict with existing overrides. The SPG API
      # will handle it and throw an error.
      for threat_id in threat_ids:
        sp_to_update.wildfireAnalysisProfile.wildfireThreatOverrides.append(
            self.messages.WildfireThreatOverride(
                threatId=threat_id, action=action_enum
            )
        )
      update_mask = 'wildfire_analysis_profile.wildfire_threat_overrides'
    # --wildfire modifies WildfireOverride.
    elif wildfire_protocols:
      # Allow multiple protocols, and remove duplicates.
      wildfire_protocols = sorted(set(wildfire_protocols))
      action_enum = self.messages.WildfireOverride.ActionValueValuesEnum(
          action_str
      )
      if sp_to_update.wildfireAnalysisProfile.wildfireOverrides is None:
        sp_to_update.wildfireAnalysisProfile.wildfireOverrides = []
      for protocol in wildfire_protocols:
        wildfire_protocol_enum = (
            self.messages.WildfireOverride.ProtocolValueValuesEnum(
                'WILDFIRE_' + protocol
            )
        )
        sp_to_update.wildfireAnalysisProfile.wildfireOverrides.append(
            self.messages.WildfireOverride(
                protocol=wildfire_protocol_enum,
                action=action_enum,
            )
        )
      update_mask = 'wildfire_analysis_profile.wildfire_overrides'
    # --wildfire-inline-ml modifies WildfireInlineMlOverride.
    elif wildfire_inline_ml_protocols:
      # Allow multiple protocols, and remove duplicates.
      wildfire_inline_ml_protocols = sorted(set(wildfire_inline_ml_protocols))
      action_enum = (
          self.messages.WildfireInlineMlOverride.ActionValueValuesEnum(
              action_str
          )
      )
      if sp_to_update.wildfireAnalysisProfile.wildfireInlineMlOverrides is None:
        sp_to_update.wildfireAnalysisProfile.wildfireInlineMlOverrides = []
      for protocol in wildfire_inline_ml_protocols:
        wildfire_inline_ml_protocol_enum = (
            self.messages.WildfireInlineMlOverride.ProtocolValueValuesEnum(
                'WILDFIRE_' + protocol
            )
        )
        sp_to_update.wildfireAnalysisProfile.wildfireInlineMlOverrides.append(
            self.messages.WildfireInlineMlOverride(
                protocol=wildfire_inline_ml_protocol_enum,
                action=action_enum,
            )
        )
      update_mask = 'wildfire_analysis_profile.wildfire_inline_ml_overrides'

    patch_request = self.messages.NetworksecurityOrganizationsLocationsSecurityProfilesPatchRequest(
        name=name,
        securityProfile=sp_to_update,
        updateMask=update_mask,
    )
    return self._security_profile_client.Patch(patch_request)
