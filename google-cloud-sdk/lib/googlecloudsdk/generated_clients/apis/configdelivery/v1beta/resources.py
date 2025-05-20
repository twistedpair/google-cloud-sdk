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


BASE_URL = 'https://configdelivery.googleapis.com/v1beta/'
DOCS_URL = 'https://cloud.google.com/anthos-config-management/config-delivery/private-preview-user-guide'


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
  PROJECTS_LOCATIONS_CONNECTIONS_REPOSITORIES = (
      'projects.locations.connections.repositories',
      'projects/{projectsId}/locations/{locationsId}/connections/'
      '{connectionsId}/repositories/{repositoriesId}',
      {},
      ['projectsId', 'locationsId', 'connectionsId', 'repositoriesId'],
      True
  )
  PROJECTS_LOCATIONS_FLEETPACKAGES = (
      'projects.locations.fleetPackages',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/fleetPackages/'
              '{fleetPackagesId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_FLEETPACKAGES_ROLLOUTS = (
      'projects.locations.fleetPackages.rollouts',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/fleetPackages/'
              '{fleetPackagesId}/rollouts/{rolloutsId}',
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
  PROJECTS_LOCATIONS_RESOURCEBUNDLES = (
      'projects.locations.resourceBundles',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/resourceBundles/'
              '{resourceBundlesId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_RESOURCEBUNDLES_RELEASES = (
      'projects.locations.resourceBundles.releases',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/resourceBundles/'
              '{resourceBundlesId}/releases/{releasesId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_RESOURCEBUNDLES_RELEASES_VARIANTS = (
      'projects.locations.resourceBundles.releases.variants',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/resourceBundles/'
              '{resourceBundlesId}/releases/{releasesId}/variants/'
              '{variantsId}',
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
