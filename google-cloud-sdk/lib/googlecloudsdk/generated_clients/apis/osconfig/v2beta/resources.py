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


BASE_URL = 'https://osconfig.googleapis.com/v2beta/'
DOCS_URL = 'https://cloud.google.com/compute/docs/osconfig/rest'


class Collections(enum.Enum):
  """Collections for all supported apis."""

  FOLDERS = (
      'folders',
      'folders/{foldersId}',
      {},
      ['foldersId'],
      True
  )
  FOLDERS_LOCATIONS = (
      'folders.locations',
      'folders/{foldersId}/locations/{locationsId}',
      {},
      ['foldersId', 'locationsId'],
      True
  )
  FOLDERS_LOCATIONS_GLOBAL = (
      'folders.locations.global',
      'folders/{foldersId}/locations/global',
      {},
      ['foldersId'],
      True
  )
  FOLDERS_LOCATIONS_GLOBAL_POLICYORCHESTRATORS = (
      'folders.locations.global.policyOrchestrators',
      '{+name}',
      {
          '':
              'folders/{foldersId}/locations/global/policyOrchestrators/'
              '{policyOrchestratorsId}',
      },
      ['name'],
      True
  )
  FOLDERS_LOCATIONS_OPERATIONS = (
      'folders.locations.operations',
      '{+name}',
      {
          '':
              'folders/{foldersId}/locations/{locationsId}/operations/'
              '{operationsId}',
      },
      ['name'],
      True
  )
  ORGANIZATIONS = (
      'organizations',
      'organizations/{organizationsId}',
      {},
      ['organizationsId'],
      True
  )
  ORGANIZATIONS_LOCATIONS = (
      'organizations.locations',
      'organizations/{organizationsId}/locations/{locationsId}',
      {},
      ['organizationsId', 'locationsId'],
      True
  )
  ORGANIZATIONS_LOCATIONS_GLOBAL = (
      'organizations.locations.global',
      'organizations/{organizationsId}/locations/global',
      {},
      ['organizationsId'],
      True
  )
  ORGANIZATIONS_LOCATIONS_GLOBAL_POLICYORCHESTRATORS = (
      'organizations.locations.global.policyOrchestrators',
      '{+name}',
      {
          '':
              'organizations/{organizationsId}/locations/global/'
              'policyOrchestrators/{policyOrchestratorsId}',
      },
      ['name'],
      True
  )
  ORGANIZATIONS_LOCATIONS_OPERATIONS = (
      'organizations.locations.operations',
      '{+name}',
      {
          '':
              'organizations/{organizationsId}/locations/{locationsId}/'
              'operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS = (
      'projects',
      'projects/{projectsId}',
      {},
      ['projectsId'],
      True
  )
  PROJECTS_LOCATIONS = (
      'projects.locations',
      'projects/{projectsId}/locations/{locationsId}',
      {},
      ['projectsId', 'locationsId'],
      True
  )
  PROJECTS_LOCATIONS_GLOBAL = (
      'projects.locations.global',
      'projects/{projectsId}/locations/global',
      {},
      ['projectsId'],
      True
  )
  PROJECTS_LOCATIONS_GLOBAL_POLICYORCHESTRATORS = (
      'projects.locations.global.policyOrchestrators',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/global/policyOrchestrators/'
              '{policyOrchestratorsId}',
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

  def __init__(self, collection_name, path, flat_paths, params,
               enable_uri_parsing):
    self.collection_name = collection_name
    self.path = path
    self.flat_paths = flat_paths
    self.params = params
    self.enable_uri_parsing = enable_uri_parsing
