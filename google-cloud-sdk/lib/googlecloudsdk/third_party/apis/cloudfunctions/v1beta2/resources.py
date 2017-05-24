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


BASE_URL = 'https://cloudfunctions.googleapis.com/v1beta2/'


class Collections(enum.Enum):
  """Collections for all supported apis."""

  OPERATIONS = (
      'operations',
      '{+name}',
      {
          '':
              'operations/{operationsId}',
      },
      [u'name']
  )
  PROJECTS = (
      'projects',
      'projects/{projectsId}',
      {},
      [u'projectsId']
  )
  PROJECTS_BUCKETS = (
      'projects.buckets',
      'projects/_/buckets/{bucketId}',
      {},
      ['bucketId']
  )
  PROJECTS_LOCATIONS = (
      'projects.locations',
      'projects/{projectsId}/locations/{locationsId}',
      {},
      [u'projectsId', u'locationsId']
  )
  PROJECTS_LOCATIONS_FUNCTIONS = (
      'projects.locations.functions',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/functions/'
              '{functionsId}',
      },
      [u'name']
  )
  PROVIDERS_EVENT_TYPES = (
      'providers.event_types',
      'providers/{triggerProvider}/eventTypes/{triggerEvent}',
      {},
      ['triggerProvider', 'triggerEvent']
  )

  def __init__(self, collection_name, path, flat_paths, params):
    self.collection_name = collection_name
    self.path = path
    self.flat_paths = flat_paths
    self.params = params
