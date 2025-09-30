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


BASE_URL = 'https://biglake.googleapis.com/iceberg/v1/'
DOCS_URL = 'https://cloud.google.com/bigquery/'


class Collections(enum.Enum):
  """Collections for all supported apis."""

  ICEBERG_V1_RESTCATALOG_EXTENSIONS_PROJECTS = (
      'iceberg.v1.restcatalog.extensions.projects',
      'restcatalog/extensions/projects/{projectsId}',
      {},
      ['projectsId'],
      True
  )
  ICEBERG_V1_RESTCATALOG_V1_PROJECTS = (
      'iceberg.v1.restcatalog.v1.projects',
      'restcatalog/v1/projects/{projectsId}',
      {},
      ['projectsId'],
      True
  )
  ICEBERG_V1_RESTCATALOG_V1_PROJECTS_CATALOGS = (
      'iceberg.v1.restcatalog.v1.projects.catalogs',
      'restcatalog/v1/projects/{projectsId}/catalogs/{catalogsId}',
      {},
      ['projectsId', 'catalogsId'],
      True
  )
  ICEBERG_V1_RESTCATALOG_EXTENSIONS_PROJECTS_CATALOGS = (
      'iceberg.v1.restcatalog.extensions.projects.catalogs',
      'restcatalog/extensions/{+name}',
      {
          '':
              'restcatalog/extensions/projects/{projectsId}/catalogs/'
              '{catalogsId}',
      },
      ['name'],
      True
  )
  ICEBERG_V1_RESTCATALOG_V1_PROJECTS_CATALOGS_NAMESPACES = (
      'iceberg.v1.restcatalog.v1.projects.catalogs.namespaces',
      'restcatalog/v1/{+name}',
      {
          '':
              'restcatalog/v1/projects/{projectsId}/catalogs/{catalogsId}/'
              'namespaces/{namespacesId}',
      },
      ['name'],
      True
  )
  ICEBERG_V1_RESTCATALOG_V1_PROJECTS_CATALOGS_NAMESPACES_TABLES = (
      'iceberg.v1.restcatalog.v1.projects.catalogs.namespaces.tables',
      'restcatalog/v1/{+name}',
      {
          '':
              'restcatalog/v1/projects/{projectsId}/catalogs/{catalogsId}/'
              'namespaces/{namespacesId}/tables/{tablesId}',
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
