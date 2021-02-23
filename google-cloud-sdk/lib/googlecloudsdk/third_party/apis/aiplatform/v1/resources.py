# -*- coding: utf-8 -*- #
# Copyright 2015 Google LLC. All Rights Reserved.
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


BASE_URL = 'https://aiplatform.googleapis.com/v1/'
DOCS_URL = 'https://cloud.google.com/ai-platform-unified/docs'


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
  PROJECTS_LOCATIONS_BATCHPREDICTIONJOBS = (
      'projects.locations.batchPredictionJobs',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'batchPredictionJobs/{batchPredictionJobsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_CUSTOMJOBS = (
      'projects.locations.customJobs',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/customJobs/'
              '{customJobsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_DATALABELINGJOBS = (
      'projects.locations.dataLabelingJobs',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'dataLabelingJobs/{dataLabelingJobsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_DATASETS = (
      'projects.locations.datasets',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/datasets/'
              '{datasetsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_DATASETS_ANNOTATIONSPECS = (
      'projects.locations.datasets.annotationSpecs',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/datasets/'
              '{datasetsId}/annotationSpecs/{annotationSpecsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_ENDPOINTS = (
      'projects.locations.endpoints',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/endpoints/'
              '{endpointsId}',
      },
      ['name'],
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
  PROJECTS_LOCATIONS_HYPERPARAMETERTUNINGJOBS = (
      'projects.locations.hyperparameterTuningJobs',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'hyperparameterTuningJobs/{hyperparameterTuningJobsId}',
      },
      ['name'],
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
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/models/'
              '{modelsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_MODELS_EVALUATIONS = (
      'projects.locations.models.evaluations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/models/'
              '{modelsId}/evaluations/{evaluationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_MODELS_EVALUATIONS_SLICES = (
      'projects.locations.models.evaluations.slices',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/models/'
              '{modelsId}/evaluations/{evaluationsId}/slices/{slicesId}',
      },
      ['name'],
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
  PROJECTS_LOCATIONS_SPECIALISTPOOLS = (
      'projects.locations.specialistPools',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/specialistPools/'
              '{specialistPoolsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_TRAININGPIPELINES = (
      'projects.locations.trainingPipelines',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'trainingPipelines/{trainingPipelinesId}',
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
