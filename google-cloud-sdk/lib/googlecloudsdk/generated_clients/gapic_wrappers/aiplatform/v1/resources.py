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
"""Resource definitions for Cloud Platform APIs generated from gapic."""

import enum


BASE_URL = 'https://aiplatform.googleapis.com/v1/'
DOCS_URL = 'https://cloud.google.com/ai-platform/docs'


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
      'projects/{projectsId}/locations/{locationsId}',
      {},
      ['projectsId', 'locationsId'],
      True
  )
  PROJECTS_LOCATIONS_ENDPOINTS = (
      'projects.locations.endpoints',
      'projects/{projectsId}/locations/{locationsId}/endpoints/{endpointsId}',
      {},
      ['projectsId', 'locationsId', 'endpointsId'],
      True
  )
  PROJECTS_LOCATIONS_ENDPOINTS_OPERATIONS = (
      'projects.locations.endpoints.operations',
      'projects/{projectsId}/locations/{locationsId}/endpoints/{endpointsId}/'
      'operations/{operationsId}',
      {},
      ['projectsId', 'locationsId', 'endpointsId', 'operationsId'],
      True
  )
  PROJECTS_LOCATIONS_INDEXENDPOINTS = (
      'projects.locations.indexEndpoints',
      'projects/{projectsId}/locations/{locationsId}/indexEndpoints/'
      '{indexEndpointsId}',
      {},
      ['projectsId', 'locationsId', 'indexEndpointsId'],
      True
  )
  PROJECTS_LOCATIONS_INDEXENDPOINTS_OPERATIONS = (
      'projects.locations.indexEndpoints.operations',
      'projects/{projectsId}/locations/{locationsId}/indexEndpoints/'
      '{indexEndpointsId}/operations/{operationsId}',
      {},
      ['projectsId', 'locationsId', 'indexEndpointsId', 'operationsId'],
      True
  )
  PROJECTS_LOCATIONS_INDEXES = (
      'projects.locations.indexes',
      'projects/{projectsId}/locations/{locationsId}/indexes/{indexesId}',
      {},
      ['projectsId', 'locationsId', 'indexesId'],
      True
  )
  PROJECTS_LOCATIONS_INDEXES_OPERATIONS = (
      'projects.locations.indexes.operations',
      'projects/{projectsId}/locations/{locationsId}/indexes/{indexesId}/'
      'operations/{operationsId}',
      {},
      ['projectsId', 'locationsId', 'indexesId', 'operationsId'],
      True
  )
  PROJECTS_LOCATIONS_MODELS = (
      'projects.locations.models',
      'projects/{projectsId}/locations/{locationsId}/models/{modelsId}',
      {},
      ['projectsId', 'locationsId', 'modelsId'],
      True
  )
  PROJECTS_LOCATIONS_MODELS_OPERATIONS = (
      'projects.locations.models.operations',
      'projects/{projectsId}/locations/{locationsId}/models/{modelsId}/'
      'operations/{operationsId}',
      {},
      ['projectsId', 'locationsId', 'modelsId', 'operationsId'],
      True
  )

  def __init__(self, collection_name, path, flat_paths, params,
               enable_uri_parsing):
    self.collection_name = collection_name
    self.path = path
    self.flat_paths = flat_paths
    self.params = params
    self.enable_uri_parsing = enable_uri_parsing
