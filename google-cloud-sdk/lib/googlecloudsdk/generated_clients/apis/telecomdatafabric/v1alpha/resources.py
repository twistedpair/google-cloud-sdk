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


BASE_URL = 'https://telecomdatafabric.googleapis.com/v1alpha/'
DOCS_URL = 'https://cloud.google.com/telecom-data-fabric'


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
  PROJECTS_LOCATIONS_BATCHINGESTIONPIPELINES = (
      'projects.locations.batchIngestionPipelines',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'batchIngestionPipelines/{batchIngestionPipelinesId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_DATAADAPTERS = (
      'projects.locations.dataAdapters',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/dataAdapters/'
              '{dataAdaptersId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_DATAAPISERVERS = (
      'projects.locations.dataApiServers',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/dataApiServers/'
              '{dataApiServersId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_DATAASSETMANAGERS = (
      'projects.locations.dataAssetManagers',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'dataAssetManagers/{dataAssetManagersId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_DATAASSETS = (
      'projects.locations.dataAssets',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/dataAssets/'
              '{dataAssetsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_DEPLOYMENTS = (
      'projects.locations.deployments',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/deployments/'
              '{deploymentsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_IAASMETRICSCOLLECTORS = (
      'projects.locations.iaasMetricsCollectors',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'iaasMetricsCollectors/{iaasMetricsCollectorsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_METRICSCORRELATIONS = (
      'projects.locations.metricsCorrelations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'metricsCorrelations/{metricsCorrelationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_METRICSINGESTIONPIPELINES = (
      'projects.locations.metricsIngestionPipelines',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'metricsIngestionPipelines/{metricsIngestionPipelinesId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_METRICSPROCESSORS = (
      'projects.locations.metricsProcessors',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'metricsProcessors/{metricsProcessorsId}',
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
  PROJECTS_LOCATIONS_PIPELINESCHEDULERS = (
      'projects.locations.pipelineSchedulers',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'pipelineSchedulers/{pipelineSchedulersId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_PUBLICTEMPLATES = (
      'projects.locations.publicTemplates',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/publicTemplates/'
              '{publicTemplatesId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_STREAMINGESTIONPIPELINES = (
      'projects.locations.streamIngestionPipelines',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'streamIngestionPipelines/{streamIngestionPipelinesId}',
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
