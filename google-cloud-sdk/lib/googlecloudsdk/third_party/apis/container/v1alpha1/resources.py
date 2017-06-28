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
      'projects/{projectId}',
      {},
      [u'projectId']
  )
  PROJECTS_LOCATIONS = (
      'projects.locations',
      'projects/{projectId}/locations/{location}',
      {},
      [u'projectId', u'location']
  )
  PROJECTS_LOCATIONS_CLUSTERS = (
      'projects.locations.clusters',
      'projects/{projectId}/locations/{location}/clusters/{clusterId}',
      {},
      [u'projectId', u'location', u'clusterId']
  )
  PROJECTS_LOCATIONS_CLUSTERS_NODEPOOLS = (
      'projects.locations.clusters.nodePools',
      'projects/{projectId}/locations/{location}/clusters/{clusterId}/'
      'nodePools/{nodePoolId}',
      {},
      [u'projectId', u'location', u'clusterId', u'nodePoolId']
  )
  PROJECTS_LOCATIONS_OPERATIONS = (
      'projects.locations.operations',
      'projects/{projectId}/locations/{location}/operations/{operationId}',
      {},
      [u'projectId', u'location', u'operationId']
  )
  PROJECTS_ZONES = (
      'projects.zones',
      'projects/{projectId}/zones/{zone}',
      {},
      [u'projectId', u'zone']
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
