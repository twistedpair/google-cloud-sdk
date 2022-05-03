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


BASE_URL = 'https://aiplatform.googleapis.com/v1beta1/'
DOCS_URL = 'https://cloud.google.com/vertex-ai/'


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
  PROJECTS_LOCATIONS_CUSTOMJOBS_OPERATIONS = (
      'projects.locations.customJobs.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/customJobs/'
              '{customJobsId}/operations/{operationsId}',
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
  PROJECTS_LOCATIONS_DATALABELINGJOBS_OPERATIONS = (
      'projects.locations.dataLabelingJobs.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'dataLabelingJobs/{dataLabelingJobsId}/operations/'
              '{operationsId}',
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
  PROJECTS_LOCATIONS_DATASETS_ANNOTATIONSPECS_OPERATIONS = (
      'projects.locations.datasets.annotationSpecs.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/datasets/'
              '{datasetsId}/annotationSpecs/{annotationSpecsId}/operations/'
              '{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_DATASETS_DATAITEMS = (
      'projects.locations.datasets.dataItems',
      'projects/{projectsId}/locations/{locationsId}/datasets/{datasetsId}/'
      'dataItems/{dataItemsId}',
      {},
      ['projectsId', 'locationsId', 'datasetsId', 'dataItemsId'],
      True
  )
  PROJECTS_LOCATIONS_DATASETS_DATAITEMS_ANNOTATIONS = (
      'projects.locations.datasets.dataItems.annotations',
      'projects/{projectsId}/locations/{locationsId}/datasets/{datasetsId}/'
      'dataItems/{dataItemsId}/annotations/{annotationsId}',
      {},
      ['projectsId', 'locationsId', 'datasetsId', 'dataItemsId', 'annotationsId'],
      True
  )
  PROJECTS_LOCATIONS_DATASETS_DATAITEMS_ANNOTATIONS_OPERATIONS = (
      'projects.locations.datasets.dataItems.annotations.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/datasets/'
              '{datasetsId}/dataItems/{dataItemsId}/annotations/'
              '{annotationsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_DATASETS_DATAITEMS_OPERATIONS = (
      'projects.locations.datasets.dataItems.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/datasets/'
              '{datasetsId}/dataItems/{dataItemsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_DATASETS_OPERATIONS = (
      'projects.locations.datasets.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/datasets/'
              '{datasetsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_DATASETS_SAVEDQUERIES = (
      'projects.locations.datasets.savedQueries',
      'projects/{projectsId}/locations/{locationsId}/datasets/{datasetsId}/'
      'savedQueries/{savedQueriesId}',
      {},
      ['projectsId', 'locationsId', 'datasetsId', 'savedQueriesId'],
      True
  )
  PROJECTS_LOCATIONS_DATASETS_SAVEDQUERIES_OPERATIONS = (
      'projects.locations.datasets.savedQueries.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/datasets/'
              '{datasetsId}/savedQueries/{savedQueriesId}/operations/'
              '{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_DEPLOYMENTRESOURCEPOOLS = (
      'projects.locations.deploymentResourcePools',
      'projects/{projectsId}/locations/{locationsId}/deploymentResourcePools/'
      '{deploymentResourcePoolsId}',
      {},
      ['projectsId', 'locationsId', 'deploymentResourcePoolsId'],
      True
  )
  PROJECTS_LOCATIONS_DEPLOYMENTRESOURCEPOOLS_OPERATIONS = (
      'projects.locations.deploymentResourcePools.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'deploymentResourcePools/{deploymentResourcePoolsId}/'
              'operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_EDGEDEVICES = (
      'projects.locations.edgeDevices',
      'projects/{projectsId}/locations/{locationsId}/edgeDevices/'
      '{edgeDevicesId}',
      {},
      ['projectsId', 'locationsId', 'edgeDevicesId'],
      True
  )
  PROJECTS_LOCATIONS_EDGEDEVICES_OPERATIONS = (
      'projects.locations.edgeDevices.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/edgeDevices/'
              '{edgeDevicesId}/operations/{operationsId}',
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
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/endpoints/'
              '{endpointsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_FEATURESTORES = (
      'projects.locations.featurestores',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/featurestores/'
              '{featurestoresId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_FEATURESTORES_ENTITYTYPES = (
      'projects.locations.featurestores.entityTypes',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/featurestores/'
              '{featurestoresId}/entityTypes/{entityTypesId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_FEATURESTORES_ENTITYTYPES_FEATURES = (
      'projects.locations.featurestores.entityTypes.features',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/featurestores/'
              '{featurestoresId}/entityTypes/{entityTypesId}/features/'
              '{featuresId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_FEATURESTORES_ENTITYTYPES_FEATURES_OPERATIONS = (
      'projects.locations.featurestores.entityTypes.features.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/featurestores/'
              '{featurestoresId}/entityTypes/{entityTypesId}/features/'
              '{featuresId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_FEATURESTORES_ENTITYTYPES_OPERATIONS = (
      'projects.locations.featurestores.entityTypes.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/featurestores/'
              '{featurestoresId}/entityTypes/{entityTypesId}/operations/'
              '{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_FEATURESTORES_OPERATIONS = (
      'projects.locations.featurestores.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/featurestores/'
              '{featurestoresId}/operations/{operationsId}',
      },
      ['name'],
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
  PROJECTS_LOCATIONS_HYPERPARAMETERTUNINGJOBS_OPERATIONS = (
      'projects.locations.hyperparameterTuningJobs.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'hyperparameterTuningJobs/{hyperparameterTuningJobsId}/'
              'operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_INDEXENDPOINTS = (
      'projects.locations.indexEndpoints',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/indexEndpoints/'
              '{indexEndpointsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_INDEXENDPOINTS_OPERATIONS = (
      'projects.locations.indexEndpoints.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/indexEndpoints/'
              '{indexEndpointsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_INDEXES = (
      'projects.locations.indexes',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/indexes/'
              '{indexesId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_INDEXES_OPERATIONS = (
      'projects.locations.indexes.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/indexes/'
              '{indexesId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_METADATASTORES = (
      'projects.locations.metadataStores',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/metadataStores/'
              '{metadataStoresId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_METADATASTORES_ARTIFACTS = (
      'projects.locations.metadataStores.artifacts',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/metadataStores/'
              '{metadataStoresId}/artifacts/{artifactsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_METADATASTORES_CONTEXTS = (
      'projects.locations.metadataStores.contexts',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/metadataStores/'
              '{metadataStoresId}/contexts/{contextsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_METADATASTORES_EXECUTIONS = (
      'projects.locations.metadataStores.executions',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/metadataStores/'
              '{metadataStoresId}/executions/{executionsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_METADATASTORES_METADATASCHEMAS = (
      'projects.locations.metadataStores.metadataSchemas',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/metadataStores/'
              '{metadataStoresId}/metadataSchemas/{metadataSchemasId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_MIGRATABLERESOURCES = (
      'projects.locations.migratableResources',
      'projects/{projectsId}/locations/{locationsId}/migratableResources/'
      '{migratableResourcesId}',
      {},
      ['projectsId', 'locationsId', 'migratableResourcesId'],
      True
  )
  PROJECTS_LOCATIONS_MIGRATABLERESOURCES_OPERATIONS = (
      'projects.locations.migratableResources.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'migratableResources/{migratableResourcesId}/operations/'
              '{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_MODELDEPLOYMENTMONITORINGJOBS = (
      'projects.locations.modelDeploymentMonitoringJobs',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'modelDeploymentMonitoringJobs/'
              '{modelDeploymentMonitoringJobsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_MODELDEPLOYMENTMONITORINGJOBS_OPERATIONS = (
      'projects.locations.modelDeploymentMonitoringJobs.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'modelDeploymentMonitoringJobs/'
              '{modelDeploymentMonitoringJobsId}/operations/{operationsId}',
      },
      ['name'],
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
  PROJECTS_LOCATIONS_MODELS_EVALUATIONS_OPERATIONS = (
      'projects.locations.models.evaluations.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/models/'
              '{modelsId}/evaluations/{evaluationsId}/operations/'
              '{operationsId}',
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
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/models/'
              '{modelsId}/operations/{operationsId}',
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
  PROJECTS_LOCATIONS_PIPELINEJOBS = (
      'projects.locations.pipelineJobs',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/pipelineJobs/'
              '{pipelineJobsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_PIPELINEJOBS_OPERATIONS = (
      'projects.locations.pipelineJobs.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/pipelineJobs/'
              '{pipelineJobsId}/operations/{operationsId}',
      },
      ['name'],
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
  PROJECTS_LOCATIONS_SPECIALISTPOOLS_OPERATIONS = (
      'projects.locations.specialistPools.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/specialistPools/'
              '{specialistPoolsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_STUDIES = (
      'projects.locations.studies',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/studies/'
              '{studiesId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_STUDIES_OPERATIONS = (
      'projects.locations.studies.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/studies/'
              '{studiesId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_STUDIES_TRIALS = (
      'projects.locations.studies.trials',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/studies/'
              '{studiesId}/trials/{trialsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_STUDIES_TRIALS_OPERATIONS = (
      'projects.locations.studies.trials.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/studies/'
              '{studiesId}/trials/{trialsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_TENSORBOARDS = (
      'projects.locations.tensorboards',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/tensorboards/'
              '{tensorboardsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_TENSORBOARDS_EXPERIMENTS = (
      'projects.locations.tensorboards.experiments',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/tensorboards/'
              '{tensorboardsId}/experiments/{experimentsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_TENSORBOARDS_EXPERIMENTS_OPERATIONS = (
      'projects.locations.tensorboards.experiments.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/tensorboards/'
              '{tensorboardsId}/experiments/{experimentsId}/operations/'
              '{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_TENSORBOARDS_EXPERIMENTS_RUNS = (
      'projects.locations.tensorboards.experiments.runs',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/tensorboards/'
              '{tensorboardsId}/experiments/{experimentsId}/runs/{runsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_TENSORBOARDS_EXPERIMENTS_RUNS_OPERATIONS = (
      'projects.locations.tensorboards.experiments.runs.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/tensorboards/'
              '{tensorboardsId}/experiments/{experimentsId}/runs/{runsId}/'
              'operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_TENSORBOARDS_EXPERIMENTS_RUNS_TIMESERIES = (
      'projects.locations.tensorboards.experiments.runs.timeSeries',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/tensorboards/'
              '{tensorboardsId}/experiments/{experimentsId}/runs/{runsId}/'
              'timeSeries/{timeSeriesId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_TENSORBOARDS_EXPERIMENTS_RUNS_TIMESERIES_OPERATIONS = (
      'projects.locations.tensorboards.experiments.runs.timeSeries.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/tensorboards/'
              '{tensorboardsId}/experiments/{experimentsId}/runs/{runsId}/'
              'timeSeries/{timeSeriesId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_TENSORBOARDS_OPERATIONS = (
      'projects.locations.tensorboards.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/tensorboards/'
              '{tensorboardsId}/operations/{operationsId}',
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
  PROJECTS_LOCATIONS_TRAININGPIPELINES_OPERATIONS = (
      'projects.locations.trainingPipelines.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'trainingPipelines/{trainingPipelinesId}/operations/'
              '{operationsId}',
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
