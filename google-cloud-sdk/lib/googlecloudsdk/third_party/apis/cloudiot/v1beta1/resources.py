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


BASE_URL = 'https://cloudiot.googleapis.com/v1beta1/'


class Collections(enum.Enum):
  """Collections for all supported apis."""

  PROJECTS_LOCATIONS = (
      'projects.locations',
      'projects/{projectsId}/locations/{locationsId}',
      {},
      ['projectsId', 'locationsId']
  )
  PROJECTS_LOCATIONS_REGISTRIES = (
      'projects.locations.registries',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/registries/'
              '{registriesId}',
      },
      [u'name']
  )
  PROJECTS_LOCATIONS_REGISTRIES_DEVICES = (
      'projects.locations.registries.devices',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/registries/'
              '{registriesId}/devices/{devicesId}',
      },
      [u'name']
  )
  PROJECTS_LOCATIONS_REGISTRIES_DEVICES_CONFIGVERSIONS = (
      'projects.locations.registries.devices.configVersions',
      'projects/{projectsId}/locations/{locationsId}/registries/'
      '{registriesId}/devices/{devicesId}/configVersions',
      {},
      ['projectsId', 'locationsId', 'registriesId', 'devicesId']
  )

  def __init__(self, collection_name, path, flat_paths, params):
    self.collection_name = collection_name
    self.path = path
    self.flat_paths = flat_paths
    self.params = params
