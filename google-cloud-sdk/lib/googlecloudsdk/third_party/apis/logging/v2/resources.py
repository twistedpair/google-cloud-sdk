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


BASE_URL = 'https://logging.googleapis.com/v2/'
DOCS_URL = 'https://cloud.google.com/logging/docs/'


class Collections(enum.Enum):
  """Collections for all supported apis."""

  BILLINGACCOUNTS = (
      'billingAccounts',
      'billingAccounts/{billingAccountsId}',
      {},
      [u'billingAccountsId']
  )
  BILLINGACCOUNTS_EXCLUSIONS = (
      'billingAccounts.exclusions',
      '{+name}',
      {
          '':
              'billingAccounts/{billingAccountsId}/exclusions/{exclusionsId}',
      },
      [u'name']
  )
  BILLINGACCOUNTS_SINKS = (
      'billingAccounts.sinks',
      '{+sinkName}',
      {
          '':
              'billingAccounts/{billingAccountsId}/sinks/{sinksId}',
      },
      [u'sinkName']
  )
  EXCLUSIONS = (
      'exclusions',
      '{+name}',
      {
          '':
              '{v2Id}/{v2Id1}/exclusions/{exclusionsId}',
      },
      [u'name']
  )
  FOLDERS = (
      'folders',
      'folders/{foldersId}',
      {},
      [u'foldersId']
  )
  FOLDERS_EXCLUSIONS = (
      'folders.exclusions',
      '{+name}',
      {
          '':
              'folders/{foldersId}/exclusions/{exclusionsId}',
      },
      [u'name']
  )
  FOLDERS_SINKS = (
      'folders.sinks',
      '{+sinkName}',
      {
          '':
              'folders/{foldersId}/sinks/{sinksId}',
      },
      [u'sinkName']
  )
  ORGANIZATIONS = (
      'organizations',
      'organizations/{organizationsId}',
      {},
      [u'organizationsId']
  )
  ORGANIZATIONS_EXCLUSIONS = (
      'organizations.exclusions',
      '{+name}',
      {
          '':
              'organizations/{organizationsId}/exclusions/{exclusionsId}',
      },
      [u'name']
  )
  ORGANIZATIONS_SINKS = (
      'organizations.sinks',
      '{+sinkName}',
      {
          '':
              'organizations/{organizationsId}/sinks/{sinksId}',
      },
      [u'sinkName']
  )
  PROJECTS = (
      'projects',
      'projects/{projectsId}',
      {},
      [u'projectsId']
  )
  PROJECTS_EXCLUSIONS = (
      'projects.exclusions',
      '{+name}',
      {
          '':
              'projects/{projectsId}/exclusions/{exclusionsId}',
      },
      [u'name']
  )
  PROJECTS_METRICS = (
      'projects.metrics',
      '{+metricName}',
      {
          '':
              'projects/{projectsId}/metrics/{metricsId}',
      },
      [u'metricName']
  )
  PROJECTS_SINKS = (
      'projects.sinks',
      '{+sinkName}',
      {
          '':
              'projects/{projectsId}/sinks/{sinksId}',
      },
      [u'sinkName']
  )
  SINKS = (
      'sinks',
      '{+sinkName}',
      {
          '':
              '{v2Id}/{v2Id1}/sinks/{sinksId}',
      },
      [u'sinkName']
  )

  def __init__(self, collection_name, path, flat_paths, params):
    self.collection_name = collection_name
    self.path = path
    self.flat_paths = flat_paths
    self.params = params
