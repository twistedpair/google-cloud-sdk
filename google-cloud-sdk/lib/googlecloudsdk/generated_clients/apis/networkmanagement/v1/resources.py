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


BASE_URL = 'https://networkmanagement.googleapis.com/v1/'
DOCS_URL = 'https://cloud.google.com/'


class Collections(enum.Enum):
  """Collections for all supported apis."""

  ORGANIZATIONS = (
      'organizations',
      'organizations/{organizationsId}',
      {},
      ['organizationsId'],
      True
  )
  ORGANIZATIONS_LOCATIONS = (
      'organizations.locations',
      '{+name}',
      {
          '':
              'organizations/{organizationsId}/locations/{locationsId}',
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
  ORGANIZATIONS_LOCATIONS_VPCFLOWLOGSCONFIGS = (
      'organizations.locations.vpcFlowLogsConfigs',
      '{+name}',
      {
          '':
              'organizations/{organizationsId}/locations/{locationsId}/'
              'vpcFlowLogsConfigs/{vpcFlowLogsConfigsId}',
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
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_GLOBAL_CONNECTIVITYTESTS = (
      'projects.locations.global.connectivityTests',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/global/connectivityTests/'
              '{connectivityTestsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_GLOBAL_OPERATIONS = (
      'projects.locations.global.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/global/operations/'
              '{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_NETWORKMONITORINGPROVIDERS = (
      'projects.locations.networkMonitoringProviders',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'networkMonitoringProviders/{networkMonitoringProvidersId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_NETWORKMONITORINGPROVIDERS_MONITORINGPOINTS = (
      'projects.locations.networkMonitoringProviders.monitoringPoints',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'networkMonitoringProviders/{networkMonitoringProvidersId}/'
              'monitoringPoints/{monitoringPointsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_NETWORKMONITORINGPROVIDERS_NETWORKPATHS = (
      'projects.locations.networkMonitoringProviders.networkPaths',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'networkMonitoringProviders/{networkMonitoringProvidersId}/'
              'networkPaths/{networkPathsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_NETWORKMONITORINGPROVIDERS_WEBPATHS = (
      'projects.locations.networkMonitoringProviders.webPaths',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'networkMonitoringProviders/{networkMonitoringProvidersId}/'
              'webPaths/{webPathsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_VPCFLOWLOGSCONFIGS = (
      'projects.locations.vpcFlowLogsConfigs',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'vpcFlowLogsConfigs/{vpcFlowLogsConfigsId}',
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
