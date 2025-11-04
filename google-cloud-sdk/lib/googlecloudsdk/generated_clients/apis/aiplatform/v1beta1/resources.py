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


BASE_URL = 'https://aiplatform.googleapis.com/v1beta1/'
DOCS_URL = 'https://cloud.google.com/vertex-ai/'


class Collections(enum.Enum):
  """Collections for all supported apis."""

  AGENTS = (
      'agents',
      'agents/{agentsId}',
      {},
      ['agentsId'],
      True
  )
  AGENTS_OPERATIONS = (
      'agents.operations',
      '{+name}',
      {
          '':
              'agents/{agentsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  APPS = (
      'apps',
      'apps/{appsId}',
      {},
      ['appsId'],
      True
  )
  APPS_OPERATIONS = (
      'apps.operations',
      '{+name}',
      {
          '':
              'apps/{appsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  BATCHPREDICTIONJOBS = (
      'batchPredictionJobs',
      '{+name}',
      {
          '':
              'batchPredictionJobs/{batchPredictionJobsId}',
      },
      ['name'],
      True
  )
  CUSTOMJOBS = (
      'customJobs',
      'customJobs/{customJobsId}',
      {},
      ['customJobsId'],
      True
  )
  CUSTOMJOBS_OPERATIONS = (
      'customJobs.operations',
      '{+name}',
      {
          '':
              'customJobs/{customJobsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  DATALABELINGJOBS = (
      'dataLabelingJobs',
      'dataLabelingJobs/{dataLabelingJobsId}',
      {},
      ['dataLabelingJobsId'],
      True
  )
  DATALABELINGJOBS_OPERATIONS = (
      'dataLabelingJobs.operations',
      '{+name}',
      {
          '':
              'dataLabelingJobs/{dataLabelingJobsId}/operations/'
              '{operationsId}',
      },
      ['name'],
      True
  )
  DATASETS = (
      'datasets',
      '{+name}',
      {
          '':
              'datasets/{datasetsId}',
      },
      ['name'],
      True
  )
  DATASETS_ANNOTATIONSPECS = (
      'datasets.annotationSpecs',
      'datasets/{datasetsId}/annotationSpecs/{annotationSpecsId}',
      {},
      ['datasetsId', 'annotationSpecsId'],
      True
  )
  DATASETS_ANNOTATIONSPECS_OPERATIONS = (
      'datasets.annotationSpecs.operations',
      '{+name}',
      {
          '':
              'datasets/{datasetsId}/annotationSpecs/{annotationSpecsId}/'
              'operations/{operationsId}',
      },
      ['name'],
      True
  )
  DATASETS_DATAITEMS = (
      'datasets.dataItems',
      'datasets/{datasetsId}/dataItems/{dataItemsId}',
      {},
      ['datasetsId', 'dataItemsId'],
      True
  )
  DATASETS_DATAITEMS_ANNOTATIONS = (
      'datasets.dataItems.annotations',
      'datasets/{datasetsId}/dataItems/{dataItemsId}/annotations/'
      '{annotationsId}',
      {},
      ['datasetsId', 'dataItemsId', 'annotationsId'],
      True
  )
  DATASETS_DATAITEMS_ANNOTATIONS_OPERATIONS = (
      'datasets.dataItems.annotations.operations',
      '{+name}',
      {
          '':
              'datasets/{datasetsId}/dataItems/{dataItemsId}/annotations/'
              '{annotationsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  DATASETS_DATAITEMS_OPERATIONS = (
      'datasets.dataItems.operations',
      '{+name}',
      {
          '':
              'datasets/{datasetsId}/dataItems/{dataItemsId}/operations/'
              '{operationsId}',
      },
      ['name'],
      True
  )
  DATASETS_DATASETVERSIONS = (
      'datasets.datasetVersions',
      '{+name}',
      {
          '':
              'datasets/{datasetsId}/datasetVersions/{datasetVersionsId}',
      },
      ['name'],
      True
  )
  DATASETS_OPERATIONS = (
      'datasets.operations',
      '{+name}',
      {
          '':
              'datasets/{datasetsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  DATASETS_SAVEDQUERIES = (
      'datasets.savedQueries',
      'datasets/{datasetsId}/savedQueries/{savedQueriesId}',
      {},
      ['datasetsId', 'savedQueriesId'],
      True
  )
  DATASETS_SAVEDQUERIES_OPERATIONS = (
      'datasets.savedQueries.operations',
      '{+name}',
      {
          '':
              'datasets/{datasetsId}/savedQueries/{savedQueriesId}/'
              'operations/{operationsId}',
      },
      ['name'],
      True
  )
  DEPLOYMENTRESOURCEPOOLS = (
      'deploymentResourcePools',
      'deploymentResourcePools/{deploymentResourcePoolsId}',
      {},
      ['deploymentResourcePoolsId'],
      True
  )
  DEPLOYMENTRESOURCEPOOLS_OPERATIONS = (
      'deploymentResourcePools.operations',
      '{+name}',
      {
          '':
              'deploymentResourcePools/{deploymentResourcePoolsId}/'
              'operations/{operationsId}',
      },
      ['name'],
      True
  )
  EDGEDEVICES = (
      'edgeDevices',
      'edgeDevices/{edgeDevicesId}',
      {},
      ['edgeDevicesId'],
      True
  )
  EDGEDEVICES_OPERATIONS = (
      'edgeDevices.operations',
      '{+name}',
      {
          '':
              'edgeDevices/{edgeDevicesId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  ENDPOINTS = (
      'endpoints',
      'endpoints/{endpointsId}',
      {},
      ['endpointsId'],
      True
  )
  ENDPOINTS_OPERATIONS = (
      'endpoints.operations',
      '{+name}',
      {
          '':
              'endpoints/{endpointsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  EVALUATIONITEMS = (
      'evaluationItems',
      'evaluationItems/{evaluationItemsId}',
      {},
      ['evaluationItemsId'],
      True
  )
  EVALUATIONITEMS_OPERATIONS = (
      'evaluationItems.operations',
      '{+name}',
      {
          '':
              'evaluationItems/{evaluationItemsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  EVALUATIONRUNS = (
      'evaluationRuns',
      'evaluationRuns/{evaluationRunsId}',
      {},
      ['evaluationRunsId'],
      True
  )
  EVALUATIONRUNS_OPERATIONS = (
      'evaluationRuns.operations',
      '{+name}',
      {
          '':
              'evaluationRuns/{evaluationRunsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  EVALUATIONSETS = (
      'evaluationSets',
      'evaluationSets/{evaluationSetsId}',
      {},
      ['evaluationSetsId'],
      True
  )
  EVALUATIONSETS_OPERATIONS = (
      'evaluationSets.operations',
      '{+name}',
      {
          '':
              'evaluationSets/{evaluationSetsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  EVALUATIONTASKS = (
      'evaluationTasks',
      'evaluationTasks/{evaluationTasksId}',
      {},
      ['evaluationTasksId'],
      True
  )
  EVALUATIONTASKS_OPERATIONS = (
      'evaluationTasks.operations',
      '{+name}',
      {
          '':
              'evaluationTasks/{evaluationTasksId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  EXAMPLESTORES = (
      'exampleStores',
      'exampleStores/{exampleStoresId}',
      {},
      ['exampleStoresId'],
      True
  )
  EXAMPLESTORES_OPERATIONS = (
      'exampleStores.operations',
      '{+name}',
      {
          '':
              'exampleStores/{exampleStoresId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  EXTENSIONCONTROLLERS = (
      'extensionControllers',
      'extensionControllers/{extensionControllersId}',
      {},
      ['extensionControllersId'],
      True
  )
  EXTENSIONCONTROLLERS_OPERATIONS = (
      'extensionControllers.operations',
      '{+name}',
      {
          '':
              'extensionControllers/{extensionControllersId}/operations/'
              '{operationsId}',
      },
      ['name'],
      True
  )
  EXTENSIONS = (
      'extensions',
      'extensions/{extensionsId}',
      {},
      ['extensionsId'],
      True
  )
  EXTENSIONS_OPERATIONS = (
      'extensions.operations',
      '{+name}',
      {
          '':
              'extensions/{extensionsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  FEATUREGROUPS = (
      'featureGroups',
      'featureGroups/{featureGroupsId}',
      {},
      ['featureGroupsId'],
      True
  )
  FEATUREGROUPS_FEATUREMONITORS = (
      'featureGroups.featureMonitors',
      'featureGroups/{featureGroupsId}/featureMonitors/{featureMonitorsId}',
      {},
      ['featureGroupsId', 'featureMonitorsId'],
      True
  )
  FEATUREGROUPS_FEATUREMONITORS_OPERATIONS = (
      'featureGroups.featureMonitors.operations',
      '{+name}',
      {
          '':
              'featureGroups/{featureGroupsId}/featureMonitors/'
              '{featureMonitorsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  FEATUREGROUPS_FEATURES = (
      'featureGroups.features',
      'featureGroups/{featureGroupsId}/features/{featuresId}',
      {},
      ['featureGroupsId', 'featuresId'],
      True
  )
  FEATUREGROUPS_FEATURES_OPERATIONS = (
      'featureGroups.features.operations',
      '{+name}',
      {
          '':
              'featureGroups/{featureGroupsId}/features/{featuresId}/'
              'operations/{operationsId}',
      },
      ['name'],
      True
  )
  FEATUREGROUPS_OPERATIONS = (
      'featureGroups.operations',
      '{+name}',
      {
          '':
              'featureGroups/{featureGroupsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  FEATUREONLINESTORES = (
      'featureOnlineStores',
      'featureOnlineStores/{featureOnlineStoresId}',
      {},
      ['featureOnlineStoresId'],
      True
  )
  FEATUREONLINESTORES_FEATUREVIEWS = (
      'featureOnlineStores.featureViews',
      'featureOnlineStores/{featureOnlineStoresId}/featureViews/'
      '{featureViewsId}',
      {},
      ['featureOnlineStoresId', 'featureViewsId'],
      True
  )
  FEATUREONLINESTORES_FEATUREVIEWS_OPERATIONS = (
      'featureOnlineStores.featureViews.operations',
      '{+name}',
      {
          '':
              'featureOnlineStores/{featureOnlineStoresId}/featureViews/'
              '{featureViewsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  FEATUREONLINESTORES_OPERATIONS = (
      'featureOnlineStores.operations',
      '{+name}',
      {
          '':
              'featureOnlineStores/{featureOnlineStoresId}/operations/'
              '{operationsId}',
      },
      ['name'],
      True
  )
  FEATURESTORES = (
      'featurestores',
      'featurestores/{featurestoresId}',
      {},
      ['featurestoresId'],
      True
  )
  FEATURESTORES_ENTITYTYPES = (
      'featurestores.entityTypes',
      'featurestores/{featurestoresId}/entityTypes/{entityTypesId}',
      {},
      ['featurestoresId', 'entityTypesId'],
      True
  )
  FEATURESTORES_ENTITYTYPES_FEATURES = (
      'featurestores.entityTypes.features',
      'featurestores/{featurestoresId}/entityTypes/{entityTypesId}/features/'
      '{featuresId}',
      {},
      ['featurestoresId', 'entityTypesId', 'featuresId'],
      True
  )
  FEATURESTORES_ENTITYTYPES_FEATURES_OPERATIONS = (
      'featurestores.entityTypes.features.operations',
      '{+name}',
      {
          '':
              'featurestores/{featurestoresId}/entityTypes/{entityTypesId}/'
              'features/{featuresId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  FEATURESTORES_ENTITYTYPES_OPERATIONS = (
      'featurestores.entityTypes.operations',
      '{+name}',
      {
          '':
              'featurestores/{featurestoresId}/entityTypes/{entityTypesId}/'
              'operations/{operationsId}',
      },
      ['name'],
      True
  )
  FEATURESTORES_OPERATIONS = (
      'featurestores.operations',
      '{+name}',
      {
          '':
              'featurestores/{featurestoresId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  HYPERPARAMETERTUNINGJOBS = (
      'hyperparameterTuningJobs',
      'hyperparameterTuningJobs/{hyperparameterTuningJobsId}',
      {},
      ['hyperparameterTuningJobsId'],
      True
  )
  HYPERPARAMETERTUNINGJOBS_OPERATIONS = (
      'hyperparameterTuningJobs.operations',
      '{+name}',
      {
          '':
              'hyperparameterTuningJobs/{hyperparameterTuningJobsId}/'
              'operations/{operationsId}',
      },
      ['name'],
      True
  )
  INDEXENDPOINTS = (
      'indexEndpoints',
      'indexEndpoints/{indexEndpointsId}',
      {},
      ['indexEndpointsId'],
      True
  )
  INDEXENDPOINTS_OPERATIONS = (
      'indexEndpoints.operations',
      '{+name}',
      {
          '':
              'indexEndpoints/{indexEndpointsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  INDEXES = (
      'indexes',
      'indexes/{indexesId}',
      {},
      ['indexesId'],
      True
  )
  INDEXES_OPERATIONS = (
      'indexes.operations',
      '{+name}',
      {
          '':
              'indexes/{indexesId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  METADATASTORES = (
      'metadataStores',
      'metadataStores/{metadataStoresId}',
      {},
      ['metadataStoresId'],
      True
  )
  METADATASTORES_ARTIFACTS = (
      'metadataStores.artifacts',
      'metadataStores/{metadataStoresId}/artifacts/{artifactsId}',
      {},
      ['metadataStoresId', 'artifactsId'],
      True
  )
  METADATASTORES_ARTIFACTS_OPERATIONS = (
      'metadataStores.artifacts.operations',
      '{+name}',
      {
          '':
              'metadataStores/{metadataStoresId}/artifacts/{artifactsId}/'
              'operations/{operationsId}',
      },
      ['name'],
      True
  )
  METADATASTORES_CONTEXTS = (
      'metadataStores.contexts',
      'metadataStores/{metadataStoresId}/contexts/{contextsId}',
      {},
      ['metadataStoresId', 'contextsId'],
      True
  )
  METADATASTORES_CONTEXTS_OPERATIONS = (
      'metadataStores.contexts.operations',
      '{+name}',
      {
          '':
              'metadataStores/{metadataStoresId}/contexts/{contextsId}/'
              'operations/{operationsId}',
      },
      ['name'],
      True
  )
  METADATASTORES_EXECUTIONS = (
      'metadataStores.executions',
      'metadataStores/{metadataStoresId}/executions/{executionsId}',
      {},
      ['metadataStoresId', 'executionsId'],
      True
  )
  METADATASTORES_EXECUTIONS_OPERATIONS = (
      'metadataStores.executions.operations',
      '{+name}',
      {
          '':
              'metadataStores/{metadataStoresId}/executions/{executionsId}/'
              'operations/{operationsId}',
      },
      ['name'],
      True
  )
  METADATASTORES_OPERATIONS = (
      'metadataStores.operations',
      '{+name}',
      {
          '':
              'metadataStores/{metadataStoresId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  MIGRATABLERESOURCES = (
      'migratableResources',
      'migratableResources/{migratableResourcesId}',
      {},
      ['migratableResourcesId'],
      True
  )
  MIGRATABLERESOURCES_OPERATIONS = (
      'migratableResources.operations',
      '{+name}',
      {
          '':
              'migratableResources/{migratableResourcesId}/operations/'
              '{operationsId}',
      },
      ['name'],
      True
  )
  MODELDEPLOYMENTMONITORINGJOBS = (
      'modelDeploymentMonitoringJobs',
      'modelDeploymentMonitoringJobs/{modelDeploymentMonitoringJobsId}',
      {},
      ['modelDeploymentMonitoringJobsId'],
      True
  )
  MODELDEPLOYMENTMONITORINGJOBS_OPERATIONS = (
      'modelDeploymentMonitoringJobs.operations',
      '{+name}',
      {
          '':
              'modelDeploymentMonitoringJobs/'
              '{modelDeploymentMonitoringJobsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  MODELMONITORS = (
      'modelMonitors',
      'modelMonitors/{modelMonitorsId}',
      {},
      ['modelMonitorsId'],
      True
  )
  MODELMONITORS_OPERATIONS = (
      'modelMonitors.operations',
      '{+name}',
      {
          '':
              'modelMonitors/{modelMonitorsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  MODELS = (
      'models',
      'models/{modelsId}',
      {},
      ['modelsId'],
      True
  )
  MODELS_EVALUATIONS = (
      'models.evaluations',
      'models/{modelsId}/evaluations/{evaluationsId}',
      {},
      ['modelsId', 'evaluationsId'],
      True
  )
  MODELS_EVALUATIONS_OPERATIONS = (
      'models.evaluations.operations',
      '{+name}',
      {
          '':
              'models/{modelsId}/evaluations/{evaluationsId}/operations/'
              '{operationsId}',
      },
      ['name'],
      True
  )
  MODELS_OPERATIONS = (
      'models.operations',
      '{+name}',
      {
          '':
              'models/{modelsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  NOTEBOOKEXECUTIONJOBS = (
      'notebookExecutionJobs',
      'notebookExecutionJobs/{notebookExecutionJobsId}',
      {},
      ['notebookExecutionJobsId'],
      True
  )
  NOTEBOOKEXECUTIONJOBS_OPERATIONS = (
      'notebookExecutionJobs.operations',
      '{+name}',
      {
          '':
              'notebookExecutionJobs/{notebookExecutionJobsId}/operations/'
              '{operationsId}',
      },
      ['name'],
      True
  )
  NOTEBOOKRUNTIMETEMPLATES = (
      'notebookRuntimeTemplates',
      'notebookRuntimeTemplates/{notebookRuntimeTemplatesId}',
      {},
      ['notebookRuntimeTemplatesId'],
      True
  )
  NOTEBOOKRUNTIMETEMPLATES_OPERATIONS = (
      'notebookRuntimeTemplates.operations',
      '{+name}',
      {
          '':
              'notebookRuntimeTemplates/{notebookRuntimeTemplatesId}/'
              'operations/{operationsId}',
      },
      ['name'],
      True
  )
  NOTEBOOKRUNTIMES = (
      'notebookRuntimes',
      'notebookRuntimes/{notebookRuntimesId}',
      {},
      ['notebookRuntimesId'],
      True
  )
  NOTEBOOKRUNTIMES_OPERATIONS = (
      'notebookRuntimes.operations',
      '{+name}',
      {
          '':
              'notebookRuntimes/{notebookRuntimesId}/operations/'
              '{operationsId}',
      },
      ['name'],
      True
  )
  OPERATIONS = (
      'operations',
      '{+name}',
      {
          '':
              'operations/{operationsId}',
      },
      ['name'],
      True
  )
  PERSISTENTRESOURCES = (
      'persistentResources',
      'persistentResources/{persistentResourcesId}',
      {},
      ['persistentResourcesId'],
      True
  )
  PERSISTENTRESOURCES_OPERATIONS = (
      'persistentResources.operations',
      '{+name}',
      {
          '':
              'persistentResources/{persistentResourcesId}/operations/'
              '{operationsId}',
      },
      ['name'],
      True
  )
  PIPELINEJOBS = (
      'pipelineJobs',
      'pipelineJobs/{pipelineJobsId}',
      {},
      ['pipelineJobsId'],
      True
  )
  PIPELINEJOBS_OPERATIONS = (
      'pipelineJobs.operations',
      '{+name}',
      {
          '':
              'pipelineJobs/{pipelineJobsId}/operations/{operationsId}',
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
  PROJECTS_LOCATIONS_AGENTS = (
      'projects.locations.agents',
      'projects/{projectsId}/locations/{locationsId}/agents/{agentsId}',
      {},
      ['projectsId', 'locationsId', 'agentsId'],
      True
  )
  PROJECTS_LOCATIONS_AGENTS_OPERATIONS = (
      'projects.locations.agents.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/agents/'
              '{agentsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_APPS = (
      'projects.locations.apps',
      'projects/{projectsId}/locations/{locationsId}/apps/{appsId}',
      {},
      ['projectsId', 'locationsId', 'appsId'],
      True
  )
  PROJECTS_LOCATIONS_APPS_OPERATIONS = (
      'projects.locations.apps.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/apps/{appsId}/'
              'operations/{operationsId}',
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
  PROJECTS_LOCATIONS_CACHEDCONTENTS = (
      'projects.locations.cachedContents',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/cachedContents/'
              '{cachedContentsId}',
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
  PROJECTS_LOCATIONS_DATASETS_DATASETVERSIONS = (
      'projects.locations.datasets.datasetVersions',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/datasets/'
              '{datasetsId}/datasetVersions/{datasetVersionsId}',
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
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'deploymentResourcePools/{deploymentResourcePoolsId}',
      },
      ['name'],
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
  PROJECTS_LOCATIONS_EVALUATIONITEMS = (
      'projects.locations.evaluationItems',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/evaluationItems/'
              '{evaluationItemsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_EVALUATIONITEMS_OPERATIONS = (
      'projects.locations.evaluationItems.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/evaluationItems/'
              '{evaluationItemsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_EVALUATIONRUNS = (
      'projects.locations.evaluationRuns',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/evaluationRuns/'
              '{evaluationRunsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_EVALUATIONRUNS_OPERATIONS = (
      'projects.locations.evaluationRuns.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/evaluationRuns/'
              '{evaluationRunsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_EVALUATIONSETS = (
      'projects.locations.evaluationSets',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/evaluationSets/'
              '{evaluationSetsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_EVALUATIONSETS_OPERATIONS = (
      'projects.locations.evaluationSets.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/evaluationSets/'
              '{evaluationSetsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_EVALUATIONTASKS = (
      'projects.locations.evaluationTasks',
      'projects/{projectsId}/locations/{locationsId}/evaluationTasks/'
      '{evaluationTasksId}',
      {},
      ['projectsId', 'locationsId', 'evaluationTasksId'],
      True
  )
  PROJECTS_LOCATIONS_EVALUATIONTASKS_OPERATIONS = (
      'projects.locations.evaluationTasks.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/evaluationTasks/'
              '{evaluationTasksId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_EXAMPLESTORES = (
      'projects.locations.exampleStores',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/exampleStores/'
              '{exampleStoresId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_EXAMPLESTORES_OPERATIONS = (
      'projects.locations.exampleStores.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/exampleStores/'
              '{exampleStoresId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_EXTENSIONCONTROLLERS = (
      'projects.locations.extensionControllers',
      'projects/{projectsId}/locations/{locationsId}/extensionControllers/'
      '{extensionControllersId}',
      {},
      ['projectsId', 'locationsId', 'extensionControllersId'],
      True
  )
  PROJECTS_LOCATIONS_EXTENSIONCONTROLLERS_OPERATIONS = (
      'projects.locations.extensionControllers.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'extensionControllers/{extensionControllersId}/operations/'
              '{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_EXTENSIONS = (
      'projects.locations.extensions',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/extensions/'
              '{extensionsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_EXTENSIONS_OPERATIONS = (
      'projects.locations.extensions.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/extensions/'
              '{extensionsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_FEATUREGROUPS = (
      'projects.locations.featureGroups',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/featureGroups/'
              '{featureGroupsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_FEATUREGROUPS_FEATUREMONITORS = (
      'projects.locations.featureGroups.featureMonitors',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/featureGroups/'
              '{featureGroupsId}/featureMonitors/{featureMonitorsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_FEATUREGROUPS_FEATUREMONITORS_FEATUREMONITORJOBS = (
      'projects.locations.featureGroups.featureMonitors.featureMonitorJobs',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/featureGroups/'
              '{featureGroupsId}/featureMonitors/{featureMonitorsId}/'
              'featureMonitorJobs/{featureMonitorJobsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_FEATUREGROUPS_FEATUREMONITORS_OPERATIONS = (
      'projects.locations.featureGroups.featureMonitors.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/featureGroups/'
              '{featureGroupsId}/featureMonitors/{featureMonitorsId}/'
              'operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_FEATUREGROUPS_FEATURES = (
      'projects.locations.featureGroups.features',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/featureGroups/'
              '{featureGroupsId}/features/{featuresId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_FEATUREGROUPS_FEATURES_OPERATIONS = (
      'projects.locations.featureGroups.features.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/featureGroups/'
              '{featureGroupsId}/features/{featuresId}/operations/'
              '{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_FEATUREGROUPS_OPERATIONS = (
      'projects.locations.featureGroups.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/featureGroups/'
              '{featureGroupsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_FEATUREONLINESTORES = (
      'projects.locations.featureOnlineStores',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'featureOnlineStores/{featureOnlineStoresId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_FEATUREONLINESTORES_FEATUREVIEWS = (
      'projects.locations.featureOnlineStores.featureViews',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'featureOnlineStores/{featureOnlineStoresId}/featureViews/'
              '{featureViewsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_FEATUREONLINESTORES_FEATUREVIEWS_FEATUREVIEWSYNCS = (
      'projects.locations.featureOnlineStores.featureViews.featureViewSyncs',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'featureOnlineStores/{featureOnlineStoresId}/featureViews/'
              '{featureViewsId}/featureViewSyncs/{featureViewSyncsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_FEATUREONLINESTORES_FEATUREVIEWS_OPERATIONS = (
      'projects.locations.featureOnlineStores.featureViews.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'featureOnlineStores/{featureOnlineStoresId}/featureViews/'
              '{featureViewsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_FEATUREONLINESTORES_OPERATIONS = (
      'projects.locations.featureOnlineStores.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'featureOnlineStores/{featureOnlineStoresId}/operations/'
              '{operationsId}',
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
  PROJECTS_LOCATIONS_METADATASTORES_ARTIFACTS_OPERATIONS = (
      'projects.locations.metadataStores.artifacts.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/metadataStores/'
              '{metadataStoresId}/artifacts/{artifactsId}/operations/'
              '{operationsId}',
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
  PROJECTS_LOCATIONS_METADATASTORES_CONTEXTS_OPERATIONS = (
      'projects.locations.metadataStores.contexts.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/metadataStores/'
              '{metadataStoresId}/contexts/{contextsId}/operations/'
              '{operationsId}',
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
  PROJECTS_LOCATIONS_METADATASTORES_EXECUTIONS_OPERATIONS = (
      'projects.locations.metadataStores.executions.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/metadataStores/'
              '{metadataStoresId}/executions/{executionsId}/operations/'
              '{operationsId}',
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
  PROJECTS_LOCATIONS_METADATASTORES_OPERATIONS = (
      'projects.locations.metadataStores.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/metadataStores/'
              '{metadataStoresId}/operations/{operationsId}',
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
  PROJECTS_LOCATIONS_MODELMONITORS = (
      'projects.locations.modelMonitors',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/modelMonitors/'
              '{modelMonitorsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_MODELMONITORS_MODELMONITORINGJOBS = (
      'projects.locations.modelMonitors.modelMonitoringJobs',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/modelMonitors/'
              '{modelMonitorsId}/modelMonitoringJobs/{modelMonitoringJobsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_MODELMONITORS_OPERATIONS = (
      'projects.locations.modelMonitors.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/modelMonitors/'
              '{modelMonitorsId}/operations/{operationsId}',
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
  PROJECTS_LOCATIONS_NASJOBS = (
      'projects.locations.nasJobs',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/nasJobs/'
              '{nasJobsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_NASJOBS_NASTRIALDETAILS = (
      'projects.locations.nasJobs.nasTrialDetails',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/nasJobs/'
              '{nasJobsId}/nasTrialDetails/{nasTrialDetailsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_NOTEBOOKEXECUTIONJOBS = (
      'projects.locations.notebookExecutionJobs',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'notebookExecutionJobs/{notebookExecutionJobsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_NOTEBOOKEXECUTIONJOBS_OPERATIONS = (
      'projects.locations.notebookExecutionJobs.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'notebookExecutionJobs/{notebookExecutionJobsId}/operations/'
              '{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_NOTEBOOKRUNTIMETEMPLATES = (
      'projects.locations.notebookRuntimeTemplates',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'notebookRuntimeTemplates/{notebookRuntimeTemplatesId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_NOTEBOOKRUNTIMETEMPLATES_OPERATIONS = (
      'projects.locations.notebookRuntimeTemplates.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'notebookRuntimeTemplates/{notebookRuntimeTemplatesId}/'
              'operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_NOTEBOOKRUNTIMES = (
      'projects.locations.notebookRuntimes',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'notebookRuntimes/{notebookRuntimesId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_NOTEBOOKRUNTIMES_OPERATIONS = (
      'projects.locations.notebookRuntimes.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'notebookRuntimes/{notebookRuntimesId}/operations/'
              '{operationsId}',
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
  PROJECTS_LOCATIONS_PERSISTENTRESOURCES = (
      'projects.locations.persistentResources',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'persistentResources/{persistentResourcesId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_PERSISTENTRESOURCES_OPERATIONS = (
      'projects.locations.persistentResources.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'persistentResources/{persistentResourcesId}/operations/'
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
  PROJECTS_LOCATIONS_RAGCORPORA = (
      'projects.locations.ragCorpora',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/ragCorpora/'
              '{ragCorporaId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_RAGCORPORA_OPERATIONS = (
      'projects.locations.ragCorpora.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/ragCorpora/'
              '{ragCorporaId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_RAGCORPORA_RAGFILES = (
      'projects.locations.ragCorpora.ragFiles',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/ragCorpora/'
              '{ragCorporaId}/ragFiles/{ragFilesId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_RAGCORPORA_RAGFILES_OPERATIONS = (
      'projects.locations.ragCorpora.ragFiles.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/ragCorpora/'
              '{ragCorporaId}/ragFiles/{ragFilesId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_RAGENGINECONFIG_OPERATIONS = (
      'projects.locations.ragEngineConfig.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/ragEngineConfig/'
              'operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_REASONINGENGINES = (
      'projects.locations.reasoningEngines',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'reasoningEngines/{reasoningEnginesId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_REASONINGENGINES_EXAMPLES = (
      'projects.locations.reasoningEngines.examples',
      'projects/{projectsId}/locations/{locationsId}/reasoningEngines/'
      '{reasoningEnginesId}/examples/{examplesId}',
      {},
      ['projectsId', 'locationsId', 'reasoningEnginesId', 'examplesId'],
      True
  )
  PROJECTS_LOCATIONS_REASONINGENGINES_EXAMPLES_OPERATIONS = (
      'projects.locations.reasoningEngines.examples.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'reasoningEngines/{reasoningEnginesId}/examples/{examplesId}/'
              'operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_REASONINGENGINES_MEMORIES = (
      'projects.locations.reasoningEngines.memories',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'reasoningEngines/{reasoningEnginesId}/memories/{memoriesId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_REASONINGENGINES_MEMORIES_OPERATIONS = (
      'projects.locations.reasoningEngines.memories.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'reasoningEngines/{reasoningEnginesId}/memories/{memoriesId}/'
              'operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_REASONINGENGINES_MEMORIES_REVISIONS = (
      'projects.locations.reasoningEngines.memories.revisions',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'reasoningEngines/{reasoningEnginesId}/memories/{memoriesId}/'
              'revisions/{revisionsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_REASONINGENGINES_OPERATIONS = (
      'projects.locations.reasoningEngines.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'reasoningEngines/{reasoningEnginesId}/operations/'
              '{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_REASONINGENGINES_SANDBOXENVIRONMENTS = (
      'projects.locations.reasoningEngines.sandboxEnvironments',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'reasoningEngines/{reasoningEnginesId}/sandboxEnvironments/'
              '{sandboxEnvironmentsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_REASONINGENGINES_SANDBOXENVIRONMENTS_OPERATIONS = (
      'projects.locations.reasoningEngines.sandboxEnvironments.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'reasoningEngines/{reasoningEnginesId}/sandboxEnvironments/'
              '{sandboxEnvironmentsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_REASONINGENGINES_SESSIONS = (
      'projects.locations.reasoningEngines.sessions',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'reasoningEngines/{reasoningEnginesId}/sessions/{sessionsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_REASONINGENGINES_SESSIONS_OPERATIONS = (
      'projects.locations.reasoningEngines.sessions.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'reasoningEngines/{reasoningEnginesId}/sessions/{sessionsId}/'
              'operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_SCHEDULES = (
      'projects.locations.schedules',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/schedules/'
              '{schedulesId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_SCHEDULES_OPERATIONS = (
      'projects.locations.schedules.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/schedules/'
              '{schedulesId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_SERVERLESSRAYJOBS = (
      'projects.locations.serverlessRayJobs',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'serverlessRayJobs/{serverlessRayJobsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_SOLVERS = (
      'projects.locations.solvers',
      'projects/{projectsId}/locations/{locationsId}/solvers/{solversId}',
      {},
      ['projectsId', 'locationsId', 'solversId'],
      True
  )
  PROJECTS_LOCATIONS_SOLVERS_OPERATIONS = (
      'projects.locations.solvers.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/solvers/'
              '{solversId}/operations/{operationsId}',
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
  PROJECTS_LOCATIONS_TUNINGJOBS = (
      'projects.locations.tuningJobs',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/tuningJobs/'
              '{tuningJobsId}',
      },
      ['name'],
      True
  )
  PUBLISHERS = (
      'publishers',
      'publishers/{publishersId}',
      {},
      ['publishersId'],
      True
  )
  PUBLISHERS_MODELS = (
      'publishers.models',
      '{+name}',
      {
          '':
              'publishers/{publishersId}/models/{modelsId}',
      },
      ['name'],
      True
  )
  RAGCORPORA = (
      'ragCorpora',
      'ragCorpora/{ragCorporaId}',
      {},
      ['ragCorporaId'],
      True
  )
  RAGCORPORA_OPERATIONS = (
      'ragCorpora.operations',
      '{+name}',
      {
          '':
              'ragCorpora/{ragCorporaId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  RAGCORPORA_RAGFILES = (
      'ragCorpora.ragFiles',
      'ragCorpora/{ragCorporaId}/ragFiles/{ragFilesId}',
      {},
      ['ragCorporaId', 'ragFilesId'],
      True
  )
  RAGCORPORA_RAGFILES_OPERATIONS = (
      'ragCorpora.ragFiles.operations',
      '{+name}',
      {
          '':
              'ragCorpora/{ragCorporaId}/ragFiles/{ragFilesId}/operations/'
              '{operationsId}',
      },
      ['name'],
      True
  )
  RAGENGINECONFIG_OPERATIONS = (
      'ragEngineConfig.operations',
      '{+name}',
      {
          '':
              'ragEngineConfig/operations/{operationsId}',
      },
      ['name'],
      True
  )
  REASONINGENGINES = (
      'reasoningEngines',
      '{+name}',
      {
          '':
              'reasoningEngines/{reasoningEnginesId}',
      },
      ['name'],
      True
  )
  REASONINGENGINES_EXAMPLES = (
      'reasoningEngines.examples',
      'reasoningEngines/{reasoningEnginesId}/examples/{examplesId}',
      {},
      ['reasoningEnginesId', 'examplesId'],
      True
  )
  REASONINGENGINES_EXAMPLES_OPERATIONS = (
      'reasoningEngines.examples.operations',
      '{+name}',
      {
          '':
              'reasoningEngines/{reasoningEnginesId}/examples/{examplesId}/'
              'operations/{operationsId}',
      },
      ['name'],
      True
  )
  REASONINGENGINES_MEMORIES = (
      'reasoningEngines.memories',
      '{+name}',
      {
          '':
              'reasoningEngines/{reasoningEnginesId}/memories/{memoriesId}',
      },
      ['name'],
      True
  )
  REASONINGENGINES_MEMORIES_OPERATIONS = (
      'reasoningEngines.memories.operations',
      '{+name}',
      {
          '':
              'reasoningEngines/{reasoningEnginesId}/memories/{memoriesId}/'
              'operations/{operationsId}',
      },
      ['name'],
      True
  )
  REASONINGENGINES_MEMORIES_REVISIONS = (
      'reasoningEngines.memories.revisions',
      '{+name}',
      {
          '':
              'reasoningEngines/{reasoningEnginesId}/memories/{memoriesId}/'
              'revisions/{revisionsId}',
      },
      ['name'],
      True
  )
  REASONINGENGINES_OPERATIONS = (
      'reasoningEngines.operations',
      '{+name}',
      {
          '':
              'reasoningEngines/{reasoningEnginesId}/operations/'
              '{operationsId}',
      },
      ['name'],
      True
  )
  REASONINGENGINES_SANDBOXENVIRONMENTS = (
      'reasoningEngines.sandboxEnvironments',
      'reasoningEngines/{reasoningEnginesId}/sandboxEnvironments/'
      '{sandboxEnvironmentsId}',
      {},
      ['reasoningEnginesId', 'sandboxEnvironmentsId'],
      True
  )
  REASONINGENGINES_SANDBOXENVIRONMENTS_OPERATIONS = (
      'reasoningEngines.sandboxEnvironments.operations',
      '{+name}',
      {
          '':
              'reasoningEngines/{reasoningEnginesId}/sandboxEnvironments/'
              '{sandboxEnvironmentsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  REASONINGENGINES_SESSIONS = (
      'reasoningEngines.sessions',
      '{+name}',
      {
          '':
              'reasoningEngines/{reasoningEnginesId}/sessions/{sessionsId}',
      },
      ['name'],
      True
  )
  REASONINGENGINES_SESSIONS_OPERATIONS = (
      'reasoningEngines.sessions.operations',
      '{+name}',
      {
          '':
              'reasoningEngines/{reasoningEnginesId}/sessions/{sessionsId}/'
              'operations/{operationsId}',
      },
      ['name'],
      True
  )
  SCHEDULES = (
      'schedules',
      'schedules/{schedulesId}',
      {},
      ['schedulesId'],
      True
  )
  SCHEDULES_OPERATIONS = (
      'schedules.operations',
      '{+name}',
      {
          '':
              'schedules/{schedulesId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  SOLVERS = (
      'solvers',
      'solvers/{solversId}',
      {},
      ['solversId'],
      True
  )
  SOLVERS_OPERATIONS = (
      'solvers.operations',
      '{+name}',
      {
          '':
              'solvers/{solversId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  SPECIALISTPOOLS = (
      'specialistPools',
      'specialistPools/{specialistPoolsId}',
      {},
      ['specialistPoolsId'],
      True
  )
  SPECIALISTPOOLS_OPERATIONS = (
      'specialistPools.operations',
      '{+name}',
      {
          '':
              'specialistPools/{specialistPoolsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  STUDIES = (
      'studies',
      'studies/{studiesId}',
      {},
      ['studiesId'],
      True
  )
  STUDIES_OPERATIONS = (
      'studies.operations',
      '{+name}',
      {
          '':
              'studies/{studiesId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  STUDIES_TRIALS = (
      'studies.trials',
      'studies/{studiesId}/trials/{trialsId}',
      {},
      ['studiesId', 'trialsId'],
      True
  )
  STUDIES_TRIALS_OPERATIONS = (
      'studies.trials.operations',
      '{+name}',
      {
          '':
              'studies/{studiesId}/trials/{trialsId}/operations/'
              '{operationsId}',
      },
      ['name'],
      True
  )
  TENSORBOARDS = (
      'tensorboards',
      'tensorboards/{tensorboardsId}',
      {},
      ['tensorboardsId'],
      True
  )
  TENSORBOARDS_EXPERIMENTS = (
      'tensorboards.experiments',
      'tensorboards/{tensorboardsId}/experiments/{experimentsId}',
      {},
      ['tensorboardsId', 'experimentsId'],
      True
  )
  TENSORBOARDS_EXPERIMENTS_OPERATIONS = (
      'tensorboards.experiments.operations',
      '{+name}',
      {
          '':
              'tensorboards/{tensorboardsId}/experiments/{experimentsId}/'
              'operations/{operationsId}',
      },
      ['name'],
      True
  )
  TENSORBOARDS_EXPERIMENTS_RUNS = (
      'tensorboards.experiments.runs',
      'tensorboards/{tensorboardsId}/experiments/{experimentsId}/runs/'
      '{runsId}',
      {},
      ['tensorboardsId', 'experimentsId', 'runsId'],
      True
  )
  TENSORBOARDS_EXPERIMENTS_RUNS_OPERATIONS = (
      'tensorboards.experiments.runs.operations',
      '{+name}',
      {
          '':
              'tensorboards/{tensorboardsId}/experiments/{experimentsId}/'
              'runs/{runsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  TENSORBOARDS_EXPERIMENTS_RUNS_TIMESERIES = (
      'tensorboards.experiments.runs.timeSeries',
      'tensorboards/{tensorboardsId}/experiments/{experimentsId}/runs/'
      '{runsId}/timeSeries/{timeSeriesId}',
      {},
      ['tensorboardsId', 'experimentsId', 'runsId', 'timeSeriesId'],
      True
  )
  TENSORBOARDS_EXPERIMENTS_RUNS_TIMESERIES_OPERATIONS = (
      'tensorboards.experiments.runs.timeSeries.operations',
      '{+name}',
      {
          '':
              'tensorboards/{tensorboardsId}/experiments/{experimentsId}/'
              'runs/{runsId}/timeSeries/{timeSeriesId}/operations/'
              '{operationsId}',
      },
      ['name'],
      True
  )
  TENSORBOARDS_OPERATIONS = (
      'tensorboards.operations',
      '{+name}',
      {
          '':
              'tensorboards/{tensorboardsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  TRAININGPIPELINES = (
      'trainingPipelines',
      'trainingPipelines/{trainingPipelinesId}',
      {},
      ['trainingPipelinesId'],
      True
  )
  TRAININGPIPELINES_OPERATIONS = (
      'trainingPipelines.operations',
      '{+name}',
      {
          '':
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
