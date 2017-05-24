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


BASE_URL = 'https://logging.googleapis.com/v1beta3/'


class Collections(enum.Enum):
  """Collections for all supported apis."""

  PROJECTS = (
      'projects',
      'projects/{projectsId}',
      {},
      [u'projectsId']
  )
  PROJECTS_LOGSERVICES = (
      'projects.logServices',
      'projects/{projectsId}/logServices/{logServicesId}',
      {},
      [u'projectsId', u'logServicesId']
  )
  PROJECTS_LOGSERVICES_SINKS = (
      'projects.logServices.sinks',
      'projects/{projectsId}/logServices/{logServicesId}/sinks/{sinksId}',
      {},
      [u'projectsId', u'logServicesId', u'sinksId']
  )
  PROJECTS_LOGS = (
      'projects.logs',
      'projects/{projectsId}/logs/{logsId}',
      {},
      [u'projectsId', u'logsId']
  )
  PROJECTS_LOGS_SINKS = (
      'projects.logs.sinks',
      'projects/{projectsId}/logs/{logsId}/sinks/{sinksId}',
      {},
      [u'projectsId', u'logsId', u'sinksId']
  )
  PROJECTS_SINKS = (
      'projects.sinks',
      'projects/{projectsId}/sinks/{sinksId}',
      {},
      [u'projectsId', u'sinksId']
  )

  def __init__(self, collection_name, path, flat_paths, params):
    self.collection_name = collection_name
    self.path = path
    self.flat_paths = flat_paths
    self.params = params
