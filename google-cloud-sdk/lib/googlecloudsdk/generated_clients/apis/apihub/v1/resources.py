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


BASE_URL = 'https://apihub.googleapis.com/v1/'
DOCS_URL = 'https://cloud.google.com/apigee/docs/api-hub/what-is-api-hub'


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
  PROJECTS_LOCATIONS_APIHUBINSTANCES = (
      'projects.locations.apiHubInstances',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/apiHubInstances/'
              '{apiHubInstancesId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_APIS = (
      'projects.locations.apis',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/apis/{apisId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_APIS_VERSIONS = (
      'projects.locations.apis.versions',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/apis/{apisId}/'
              'versions/{versionsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_APIS_VERSIONS_DEFINITIONS = (
      'projects.locations.apis.versions.definitions',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/apis/{apisId}/'
              'versions/{versionsId}/definitions/{definitionsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_APIS_VERSIONS_OPERATIONS = (
      'projects.locations.apis.versions.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/apis/{apisId}/'
              'versions/{versionsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_APIS_VERSIONS_SPECS = (
      'projects.locations.apis.versions.specs',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/apis/{apisId}/'
              'versions/{versionsId}/specs/{specsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_ATTRIBUTES = (
      'projects.locations.attributes',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/attributes/'
              '{attributesId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_DEPENDENCIES = (
      'projects.locations.dependencies',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/dependencies/'
              '{dependenciesId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_DEPLOYMENTS = (
      'projects.locations.deployments',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/deployments/'
              '{deploymentsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_EXTERNALAPIS = (
      'projects.locations.externalApis',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/externalApis/'
              '{externalApisId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_HOSTPROJECTREGISTRATIONS = (
      'projects.locations.hostProjectRegistrations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'hostProjectRegistrations/{hostProjectRegistrationsId}',
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
  PROJECTS_LOCATIONS_PLUGINS = (
      'projects.locations.plugins',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/plugins/'
              '{pluginsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_RUNTIMEPROJECTATTACHMENTS = (
      'projects.locations.runtimeProjectAttachments',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'runtimeProjectAttachments/{runtimeProjectAttachmentsId}',
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
