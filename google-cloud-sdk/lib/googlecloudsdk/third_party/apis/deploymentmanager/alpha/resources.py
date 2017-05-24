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


BASE_URL = 'https://www.googleapis.com/deploymentmanager/alpha/'


class Collections(enum.Enum):
  """Collections for all supported apis."""

  COMPOSITETYPES = (
      'compositeTypes',
      'projects/{project}/global/compositeTypes/{compositeType}',
      {},
      [u'project', u'compositeType']
  )
  DEPLOYMENTS = (
      'deployments',
      'projects/{project}/global/deployments/{deployment}',
      {},
      [u'project', u'deployment']
  )
  MANIFESTS = (
      'manifests',
      'projects/{project}/global/deployments/{deployment}/manifests/'
      '{manifest}',
      {},
      [u'project', u'deployment', u'manifest']
  )
  OPERATIONS = (
      'operations',
      'projects/{project}/global/operations/{operation}',
      {},
      [u'project', u'operation']
  )
  PROJECTS = (
      'projects',
      'projects/{project}',
      {},
      [u'project']
  )
  RESOURCES = (
      'resources',
      'projects/{project}/global/deployments/{deployment}/resources/'
      '{resource}',
      {},
      [u'project', u'deployment', u'resource']
  )
  TYPEPROVIDERS = (
      'typeProviders',
      'projects/{project}/global/typeProviders/{typeProvider}',
      {},
      [u'project', u'typeProvider']
  )
  TYPES = (
      'types',
      'projects/{project}/global/types/{type}',
      {},
      [u'project', u'type']
  )

  def __init__(self, collection_name, path, flat_paths, params):
    self.collection_name = collection_name
    self.path = path
    self.flat_paths = flat_paths
    self.params = params
