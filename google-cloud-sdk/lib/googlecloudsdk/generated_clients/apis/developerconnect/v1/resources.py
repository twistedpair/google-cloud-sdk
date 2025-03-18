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


BASE_URL = 'https://developerconnect.googleapis.com/v1/'
DOCS_URL = 'http://cloud.google.com/developer-connect/docs/overview'


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
  PROJECTS_LOCATIONS_ACCOUNTCONNECTORS = (
      'projects.locations.accountConnectors',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'accountConnectors/{accountConnectorsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_CONNECTIONS = (
      'projects.locations.connections',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/connections/'
              '{connectionsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_CONNECTIONS_GITREPOSITORYLINKS = (
      'projects.locations.connections.gitRepositoryLinks',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/connections/'
              '{connectionsId}/gitRepositoryLinks/{gitRepositoryLinksId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_INSIGHTSCONFIGS = (
      'projects.locations.insightsConfigs',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/insightsConfigs/'
              '{insightsConfigsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_KEYRINGS_CRYPTOKEYS = (
      'projects.locations.keyRings.cryptoKeys',
      'projects/{projectsId}/locations/{locationsId}/keyRings/{keyRingsId}/'
      'cryptoKeys/{cryptoKeysId}',
      {},
      ['projectsId', 'locationsId', 'keyRingsId', 'cryptoKeysId'],
      True
  )
  PROJECTS_LOCATIONS_NAMESPACES_SERVICES = (
      'projects.locations.namespaces.services',
      'projects/{projectsId}/locations/{locationsId}/namespaces/'
      '{namespacesId}/services/{servicesId}',
      {},
      ['projectsId', 'locationsId', 'namespacesId', 'servicesId'],
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
  PROJECTS_SECRETS = (
      'projects.secrets',
      'projects/{projectsId}/secrets/{secretsId}',
      {},
      ['projectsId', 'secretsId'],
      True
  )
  PROJECTS_SECRETS_VERSIONS = (
      'projects.secrets.versions',
      'projects/{projectsId}/secrets/{secretsId}/versions/{versionsId}',
      {},
      ['projectsId', 'secretsId', 'versionsId'],
      True
  )

  def __init__(self, collection_name, path, flat_paths, params,
               enable_uri_parsing):
    self.collection_name = collection_name
    self.path = path
    self.flat_paths = flat_paths
    self.params = params
    self.enable_uri_parsing = enable_uri_parsing
