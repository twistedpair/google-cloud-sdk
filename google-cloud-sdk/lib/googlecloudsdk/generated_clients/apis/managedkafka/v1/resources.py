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


BASE_URL = 'https://managedkafka.googleapis.com/v1/'
DOCS_URL = 'https://cloud.google.com/managed-service-for-apache-kafka/docs'


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
  PROJECTS_LOCATIONS_CLUSTERS = (
      'projects.locations.clusters',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/clusters/'
              '{clustersId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_CLUSTERS_ACLS = (
      'projects.locations.clusters.acls',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/clusters/'
              '{clustersId}/acls/{aclsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_CLUSTERS_CONSUMERGROUPS = (
      'projects.locations.clusters.consumerGroups',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/clusters/'
              '{clustersId}/consumerGroups/{consumerGroupsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_CLUSTERS_TOPICS = (
      'projects.locations.clusters.topics',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/clusters/'
              '{clustersId}/topics/{topicsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_CONNECTCLUSTERS = (
      'projects.locations.connectClusters',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/connectClusters/'
              '{connectClustersId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_CONNECTCLUSTERS_CONNECTORS = (
      'projects.locations.connectClusters.connectors',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/connectClusters/'
              '{connectClustersId}/connectors/{connectorsId}',
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
  PROJECTS_LOCATIONS_SCHEMAREGISTRIES = (
      'projects.locations.schemaRegistries',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'schemaRegistries/{schemaRegistriesId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_SCHEMAREGISTRIES_CONFIG = (
      'projects.locations.schemaRegistries.config',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'schemaRegistries/{schemaRegistriesId}/config/{configId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_SCHEMAREGISTRIES_CONTEXTS = (
      'projects.locations.schemaRegistries.contexts',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'schemaRegistries/{schemaRegistriesId}/contexts/{contextsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_SCHEMAREGISTRIES_CONTEXTS_CONFIG = (
      'projects.locations.schemaRegistries.contexts.config',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'schemaRegistries/{schemaRegistriesId}/contexts/{contextsId}/'
              'config/{configId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_SCHEMAREGISTRIES_CONTEXTS_MODE = (
      'projects.locations.schemaRegistries.contexts.mode',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'schemaRegistries/{schemaRegistriesId}/contexts/{contextsId}/'
              'mode/{modeId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_SCHEMAREGISTRIES_CONTEXTS_SCHEMAS = (
      'projects.locations.schemaRegistries.contexts.schemas',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'schemaRegistries/{schemaRegistriesId}/contexts/{contextsId}/'
              'schemas/{schemasId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_SCHEMAREGISTRIES_CONTEXTS_SUBJECTS = (
      'projects.locations.schemaRegistries.contexts.subjects',
      'projects/{projectsId}/locations/{locationsId}/schemaRegistries/'
      '{schemaRegistriesId}/contexts/{contextsId}/subjects/{subjectsId}',
      {},
      ['projectsId', 'locationsId', 'schemaRegistriesId', 'contextsId', 'subjectsId'],
      True
  )
  PROJECTS_LOCATIONS_SCHEMAREGISTRIES_CONTEXTS_SUBJECTS_VERSIONS = (
      'projects.locations.schemaRegistries.contexts.subjects.versions',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'schemaRegistries/{schemaRegistriesId}/contexts/{contextsId}/'
              'subjects/{subjectsId}/versions/{versionsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_SCHEMAREGISTRIES_MODE = (
      'projects.locations.schemaRegistries.mode',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'schemaRegistries/{schemaRegistriesId}/mode/{modeId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_SCHEMAREGISTRIES_SCHEMAS = (
      'projects.locations.schemaRegistries.schemas',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'schemaRegistries/{schemaRegistriesId}/schemas/{schemasId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_SCHEMAREGISTRIES_SUBJECTS = (
      'projects.locations.schemaRegistries.subjects',
      'projects/{projectsId}/locations/{locationsId}/schemaRegistries/'
      '{schemaRegistriesId}/subjects/{subjectsId}',
      {},
      ['projectsId', 'locationsId', 'schemaRegistriesId', 'subjectsId'],
      True
  )
  PROJECTS_LOCATIONS_SCHEMAREGISTRIES_SUBJECTS_VERSIONS = (
      'projects.locations.schemaRegistries.subjects.versions',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'schemaRegistries/{schemaRegistriesId}/subjects/{subjectsId}/'
              'versions/{versionsId}',
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
