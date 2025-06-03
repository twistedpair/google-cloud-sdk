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


BASE_URL = 'https://designcenter.googleapis.com/v1alpha/'
DOCS_URL = 'http://cloud.google.com/application-design-center/docs'


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
  PROJECTS_LOCATIONS_SPACES = (
      'projects.locations.spaces',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/spaces/'
              '{spacesId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_SPACES_APPLICATIONTEMPLATES = (
      'projects.locations.spaces.applicationTemplates',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/spaces/'
              '{spacesId}/applicationTemplates/{applicationTemplatesId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_SPACES_APPLICATIONTEMPLATES_COMPONENTS = (
      'projects.locations.spaces.applicationTemplates.components',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/spaces/'
              '{spacesId}/applicationTemplates/{applicationTemplatesId}/'
              'components/{componentsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_SPACES_APPLICATIONTEMPLATES_COMPONENTS_CONNECTIONS = (
      'projects.locations.spaces.applicationTemplates.components.connections',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/spaces/'
              '{spacesId}/applicationTemplates/{applicationTemplatesId}/'
              'components/{componentsId}/connections/{connectionsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_SPACES_APPLICATIONTEMPLATES_REVISIONS = (
      'projects.locations.spaces.applicationTemplates.revisions',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/spaces/'
              '{spacesId}/applicationTemplates/{applicationTemplatesId}/'
              'revisions/{revisionsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_SPACES_APPLICATIONS = (
      'projects.locations.spaces.applications',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/spaces/'
              '{spacesId}/applications/{applicationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_SPACES_CATALOGS = (
      'projects.locations.spaces.catalogs',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/spaces/'
              '{spacesId}/catalogs/{catalogsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_SPACES_CATALOGS_SHARES = (
      'projects.locations.spaces.catalogs.shares',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/spaces/'
              '{spacesId}/catalogs/{catalogsId}/shares/{sharesId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_SPACES_CATALOGS_TEMPLATES = (
      'projects.locations.spaces.catalogs.templates',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/spaces/'
              '{spacesId}/catalogs/{catalogsId}/templates/{templatesId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_SPACES_CATALOGS_TEMPLATES_REVISIONS = (
      'projects.locations.spaces.catalogs.templates.revisions',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/spaces/'
              '{spacesId}/catalogs/{catalogsId}/templates/{templatesId}/'
              'revisions/{revisionsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_SPACES_SHAREDTEMPLATES = (
      'projects.locations.spaces.sharedTemplates',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/spaces/'
              '{spacesId}/sharedTemplates/{sharedTemplatesId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_SPACES_SHAREDTEMPLATES_REVISIONS = (
      'projects.locations.spaces.sharedTemplates.revisions',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/spaces/'
              '{spacesId}/sharedTemplates/{sharedTemplatesId}/revisions/'
              '{revisionsId}',
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
