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
"""Resource definitions for Cloud Platform Apis generated from apitools."""

import enum


BASE_URL = 'https://cloudaicompanion.googleapis.com/v1/'
DOCS_URL = 'https://cloud.google.com/gemini'


class Collections(enum.Enum):
  """Collections for all supported apis."""

  PROJECTS = (
      'projects',
      'projects/{projectsId}',
      {},
      ['projectsId'],
      True
  )
  PROJECTS_LOCATIONS = (
      'projects.locations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_CODEREPOSITORYINDEXES = (
      'projects.locations.codeRepositoryIndexes',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'codeRepositoryIndexes/{codeRepositoryIndexesId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_CODEREPOSITORYINDEXES_REPOSITORYGROUPS = (
      'projects.locations.codeRepositoryIndexes.repositoryGroups',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'codeRepositoryIndexes/{codeRepositoryIndexesId}/'
              'repositoryGroups/{repositoryGroupsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_CODETOOLSSETTINGS = (
      'projects.locations.codeToolsSettings',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'codeToolsSettings/{codeToolsSettingsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_CODETOOLSSETTINGS_SETTINGBINDINGS = (
      'projects.locations.codeToolsSettings.settingBindings',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'codeToolsSettings/{codeToolsSettingsId}/settingBindings/'
              '{settingBindingsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_DATASHARINGWITHGOOGLESETTINGS = (
      'projects.locations.dataSharingWithGoogleSettings',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'dataSharingWithGoogleSettings/'
              '{dataSharingWithGoogleSettingsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_DATASHARINGWITHGOOGLESETTINGS_SETTINGBINDINGS = (
      'projects.locations.dataSharingWithGoogleSettings.settingBindings',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'dataSharingWithGoogleSettings/'
              '{dataSharingWithGoogleSettingsId}/settingBindings/'
              '{settingBindingsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_GEMINIGCPENABLEMENTSETTINGS = (
      'projects.locations.geminiGcpEnablementSettings',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'geminiGcpEnablementSettings/{geminiGcpEnablementSettingsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_GEMINIGCPENABLEMENTSETTINGS_SETTINGBINDINGS = (
      'projects.locations.geminiGcpEnablementSettings.settingBindings',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'geminiGcpEnablementSettings/{geminiGcpEnablementSettingsId}/'
              'settingBindings/{settingBindingsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_LOGGINGSETTINGS = (
      'projects.locations.loggingSettings',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/loggingSettings/'
              '{loggingSettingsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_LOGGINGSETTINGS_SETTINGBINDINGS = (
      'projects.locations.loggingSettings.settingBindings',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/loggingSettings/'
              '{loggingSettingsId}/settingBindings/{settingBindingsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_OPERATIONS = (
      'projects.locations.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/operations/'
              '{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_RELEASECHANNELSETTINGS = (
      'projects.locations.releaseChannelSettings',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'releaseChannelSettings/{releaseChannelSettingsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_RELEASECHANNELSETTINGS_SETTINGBINDINGS = (
      'projects.locations.releaseChannelSettings.settingBindings',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'releaseChannelSettings/{releaseChannelSettingsId}/'
              'settingBindings/{settingBindingsId}',
      },
      ['name'],
      True
  )

  def __init__(self, collection_name, path, flat_paths, params,
               enable_uri_parsing):
    self.collection_name = collection_name
    self.path = path
    self.flat_paths = flat_paths
    self.params = params
    self.enable_uri_parsing = enable_uri_parsing
