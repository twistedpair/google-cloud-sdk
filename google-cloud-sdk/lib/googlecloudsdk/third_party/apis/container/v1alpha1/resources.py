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


BASE_URL = 'https://container.googleapis.com/v1alpha1/'


class Collections(enum.Enum):
  """Collections for all supported apis."""

  PROJECTS = (
      'projects',
      'projects/{projectsId}',
      {},
      [u'projectsId']
  )
  PROJECTS_LOCATIONS = (
      'projects.locations',
      'projects/{projectsId}/locations/{locationsId}',
      {},
      [u'projectsId', u'locationsId']
  )
  PROJECTS_LOCATIONS_CLUSTERS = (
      'projects.locations.clusters',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/clusters/'
              '{clustersId}',
      },
      [u'name']
  )
  PROJECTS_LOCATIONS_CLUSTERS_NODEPOOLS = (
      'projects.locations.clusters.nodePools',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/clusters/'
              '{clustersId}/nodePools/{nodePoolsId}',
      },
      [u'name']
  )
  PROJECTS_LOCATIONS_OPERATIONS = (
      'projects.locations.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/operations/'
              '{operationsId}',
      },
      [u'name']
  )
  PROJECTS_ZONES = (
      'projects.zones',
      'projects/{projectId}/zones/{zoneId}',
      {},
      ['projectId', 'zoneId']
  )
  PROJECTS_ZONES_CLUSTERS = (
      'projects.zones.clusters',
      'projects/{projectId}/zones/{zone}/clusters/{clusterId}',
      {},
      [u'projectId', u'zone', u'clusterId']
  )
  PROJECTS_ZONES_CLUSTERS_NODEPOOLS = (
      'projects.zones.clusters.nodePools',
      'projects/{projectId}/zones/{zone}/clusters/{clusterId}/nodePools/'
      '{nodePoolId}',
      {},
      [u'projectId', u'zone', u'clusterId', u'nodePoolId']
  )
  PROJECTS_ZONES_OPERATIONS = (
      'projects.zones.operations',
      'projects/{projectId}/zones/{zone}/operations/{operationId}',
      {},
      [u'projectId', u'zone', u'operationId']
  )

  def __init__(self, collection_name, path, flat_paths, params):
    self.collection_name = collection_name
    self.path = path
    self.flat_paths = flat_paths
    self.params = params
