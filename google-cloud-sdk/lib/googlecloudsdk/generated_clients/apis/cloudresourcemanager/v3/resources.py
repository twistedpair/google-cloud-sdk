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


BASE_URL = 'https://cloudresourcemanager.googleapis.com/v3/'
DOCS_URL = 'https://cloud.google.com/resource-manager'


class Collections(enum.Enum):
  """Collections for all supported apis."""

  FOLDERS = (
      'folders',
      '{+name}',
      {
          '':
              'folders/{foldersId}',
      },
      ['name'],
      True
  )
  FOLDERS_CAPABILITIES = (
      'folders.capabilities',
      '{+name}',
      {
          '':
              'folders/{foldersId}/capabilities/{capabilitiesId}',
      },
      ['name'],
      True
  )
  FOLDERS_EFFECTIVESETTINGS = (
      'folders.effectiveSettings',
      '{+name}',
      {
          '':
              'folders/{foldersId}/effectiveSettings/{effectiveSettingsId}',
      },
      ['name'],
      True
  )
  FOLDERS_SETTINGS = (
      'folders.settings',
      '{+name}',
      {
          '':
              'folders/{foldersId}/settings/{settingsId}',
      },
      ['name'],
      True
  )
  LIENS = (
      'liens',
      '{+name}',
      {
          '':
              'liens/{liensId}',
      },
      ['name'],
      True
  )
  LOCATIONS = (
      'locations',
      'locations/{locationsId}',
      {},
      ['locationsId'],
      True
  )
  LOCATIONS_EFFECTIVETAGBINDINGCOLLECTIONS = (
      'locations.effectiveTagBindingCollections',
      '{+name}',
      {
          '':
              'locations/{locationsId}/effectiveTagBindingCollections/'
              '{effectiveTagBindingCollectionsId}',
      },
      ['name'],
      True
  )
  LOCATIONS_TAGBINDINGCOLLECTIONS = (
      'locations.tagBindingCollections',
      '{+name}',
      {
          '':
              'locations/{locationsId}/tagBindingCollections/'
              '{tagBindingCollectionsId}',
      },
      ['name'],
      True
  )
  OPERATIONS = (
      'operations',
      '{+name}',
      {
          '':
              'operations/{operationsId}',
      },
      ['name'],
      True
  )
  ORGANIZATIONS = (
      'organizations',
      '{+name}',
      {
          '':
              'organizations/{organizationsId}',
      },
      ['name'],
      True
  )
  ORGANIZATIONS_EFFECTIVESETTINGS = (
      'organizations.effectiveSettings',
      '{+name}',
      {
          '':
              'organizations/{organizationsId}/effectiveSettings/'
              '{effectiveSettingsId}',
      },
      ['name'],
      True
  )
  ORGANIZATIONS_SETTINGS = (
      'organizations.settings',
      '{+name}',
      {
          '':
              'organizations/{organizationsId}/settings/{settingsId}',
      },
      ['name'],
      True
  )
  PROJECTS = (
      'projects',
      '{+name}',
      {
          '':
              'projects/{projectsId}',
      },
      ['name'],
      True
  )
  PROJECTS_EFFECTIVESETTINGS = (
      'projects.effectiveSettings',
      '{+name}',
      {
          '':
              'projects/{projectsId}/effectiveSettings/{effectiveSettingsId}',
      },
      ['name'],
      True
  )
  PROJECTS_SETTINGS = (
      'projects.settings',
      '{+name}',
      {
          '':
              'projects/{projectsId}/settings/{settingsId}',
      },
      ['name'],
      True
  )
  TAGKEYS = (
      'tagKeys',
      '{+name}',
      {
          '':
              'tagKeys/{tagKeysId}',
      },
      ['name'],
      True
  )
  TAGVALUES = (
      'tagValues',
      '{+name}',
      {
          '':
              'tagValues/{tagValuesId}',
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
