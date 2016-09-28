# Copyright 2015 Google Inc. All Rights Reserved.
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
"""Resource definitions for cloud platform apis."""

import enum


BASE_URL = 'https://appengine.googleapis.com/v1/'


class Collections(enum.Enum):
  """Collections for all supported apis."""

  APPS = (
      'apps',
      '{+name}',
      {
          '':
              'apps/{appsId}',
      },
      [u'name'],
      'AppengineAppsGetRequest',)
  APPS_LOCATIONS = (
      'apps.locations',
      '{+name}',
      {
          '':
              'apps/{appsId}/locations/{locationsId}',
      },
      [u'name'],
      'AppengineAppsLocationsGetRequest',)
  APPS_OPERATIONS = (
      'apps.operations',
      '{+name}',
      {
          '':
              'apps/{appsId}/operations/{operationsId}',
      },
      [u'name'],
      'AppengineAppsOperationsGetRequest',)
  APPS_SERVICES = (
      'apps.services',
      '{+name}',
      {
          '':
              'apps/{appsId}/services/{servicesId}',
      },
      [u'name'],
      'AppengineAppsServicesGetRequest',)
  APPS_SERVICES_VERSIONS = (
      'apps.services.versions',
      '{+name}',
      {
          '':
              'apps/{appsId}/services/{servicesId}/versions/{versionsId}',
      },
      [u'name'],
      'AppengineAppsServicesVersionsGetRequest',)
  APPS_SERVICES_VERSIONS_INSTANCES = (
      'apps.services.versions.instances',
      '{+name}',
      {
          '':
              'apps/{appsId}/services/{servicesId}/versions/{versionsId}/'
              'instances/{instancesId}',
      },
      [u'name'],
      'AppengineAppsServicesVersionsInstancesGetRequest',)
  EXPERIMENTAL_APPS_OPERATIONS = (
      'experimental.apps.operations',
      '{+name}',
      {
          '':
              'apps/{appsId}/operations/{operationsId}',
      },
      [u'name'],
      'AppengineExperimentalAppsOperationsGetRequest',)

  def __init__(self, collection_name, path, flat_paths, params, request_type):
    self.collection_name = collection_name
    self.path = path
    self.flat_paths = flat_paths
    self.params = params
    self.request_type = request_type
