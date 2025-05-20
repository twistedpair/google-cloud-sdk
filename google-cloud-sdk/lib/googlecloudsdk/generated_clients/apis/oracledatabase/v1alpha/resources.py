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


BASE_URL = 'https://oracledatabase.googleapis.com/v1alpha/'
DOCS_URL = 'https://cloud.google.com/oracle/database/docs'


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
  PROJECTS_LOCATIONS_AUTONOMOUSDATABASEBACKUPS = (
      'projects.locations.autonomousDatabaseBackups',
      'projects/{projectsId}/locations/{locationsId}/'
      'autonomousDatabaseBackups/{autonomousDatabaseBackupsId}',
      {},
      ['projectsId', 'locationsId', 'autonomousDatabaseBackupsId'],
      True
  )
  PROJECTS_LOCATIONS_AUTONOMOUSDATABASECHARACTERSETS = (
      'projects.locations.autonomousDatabaseCharacterSets',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'autonomousDatabaseCharacterSets/'
              '{autonomousDatabaseCharacterSetsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_AUTONOMOUSDATABASES = (
      'projects.locations.autonomousDatabases',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'autonomousDatabases/{autonomousDatabasesId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_AUTONOMOUSDBVERSIONS = (
      'projects.locations.autonomousDbVersions',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'autonomousDbVersions/{autonomousDbVersionsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_CLOUDEXADATAINFRASTRUCTURES = (
      'projects.locations.cloudExadataInfrastructures',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'cloudExadataInfrastructures/{cloudExadataInfrastructuresId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_CLOUDEXADATAINFRASTRUCTURES_DBSERVERS = (
      'projects.locations.cloudExadataInfrastructures.dbServers',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'cloudExadataInfrastructures/{cloudExadataInfrastructuresId}/'
              'dbServers/{dbServersId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_CLOUDVMCLUSTERS = (
      'projects.locations.cloudVmClusters',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/cloudVmClusters/'
              '{cloudVmClustersId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_CLOUDVMCLUSTERS_DBNODES = (
      'projects.locations.cloudVmClusters.dbNodes',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/cloudVmClusters/'
              '{cloudVmClustersId}/dbNodes/{dbNodesId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_DBSYSTEMSHAPES = (
      'projects.locations.dbSystemShapes',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/dbSystemShapes/'
              '{dbSystemShapesId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_ENTITLEMENTS = (
      'projects.locations.entitlements',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/entitlements/'
              '{entitlementsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_EXADBVMCLUSTERS = (
      'projects.locations.exadbVmClusters',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/exadbVmClusters/'
              '{exadbVmClustersId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_EXADBVMCLUSTERS_DBNODES = (
      'projects.locations.exadbVmClusters.dbNodes',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/exadbVmClusters/'
              '{exadbVmClustersId}/dbNodes/{dbNodesId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_EXASCALEDBSTORAGEVAULTS = (
      'projects.locations.exascaleDbStorageVaults',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'exascaleDbStorageVaults/{exascaleDbStorageVaultsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_GIVERSIONS = (
      'projects.locations.giVersions',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/giVersions/'
              '{giVersionsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_GIVERSIONS_MINORVERSIONS = (
      'projects.locations.giVersions.minorVersions',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/giVersions/'
              '{giVersionsId}/minorVersions/{minorVersionsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_ODBNETWORKS = (
      'projects.locations.odbNetworks',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/odbNetworks/'
              '{odbNetworksId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_ODBNETWORKS_ODBSUBNETS = (
      'projects.locations.odbNetworks.odbSubnets',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/odbNetworks/'
              '{odbNetworksId}/odbSubnets/{odbSubnetsId}',
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
  PROJECTS_LOCATIONS_SYSTEMVERSIONS = (
      'projects.locations.systemVersions',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/systemVersions/'
              '{systemVersionsId}',
      },
      ['name'],
      True
  )
  PROJECTS_NETWORKS = (
      'projects.networks',
      'projects/{projectsId}/global/networks/{networksId}',
      {},
      ['projectsId', 'networksId'],
      True
  )

  def __init__(self, collection_name, path, flat_paths, params,
               enable_uri_parsing):
    self.collection_name = collection_name
    self.path = path
    self.flat_paths = flat_paths
    self.params = params
    self.enable_uri_parsing = enable_uri_parsing
