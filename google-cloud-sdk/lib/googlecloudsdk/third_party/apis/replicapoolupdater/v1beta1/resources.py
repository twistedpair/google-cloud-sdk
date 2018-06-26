# -*- coding: utf-8 -*- #
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


BASE_URL = 'https://www.googleapis.com/replicapoolupdater/v1beta1/'
DOCS_URL = 'https://cloud.google.com/compute/docs/instance-groups/manager/#applying_rolling_updates_using_the_updater_service'


class Collections(enum.Enum):
  """Collections for all supported apis."""

  PROJECTS = (
      'projects',
      'projects/{project}',
      {},
      [u'project'],
      True
  )
  ROLLINGUPDATES = (
      'rollingUpdates',
      'projects/{project}/zones/{zone}/rollingUpdates/{rollingUpdate}',
      {},
      [u'project', u'zone', u'rollingUpdate'],
      True
  )
  ROLLOUT = (
      'rollout',
      'projects/{project}/zones/{zone}/rollouts/{rollout}',
      {},
      [u'project', u'zone', u'rollout'],
      True
  )
  ZONEOPERATIONS = (
      'zoneOperations',
      'projects/{project}/zones/{zone}/operations/{operation}',
      {},
      [u'project', u'zone', u'operation'],
      True
  )
  ZONES = (
      'zones',
      'projects/{project}/zones/{zone}',
      {},
      [u'project', u'zone'],
      True
  )

  def __init__(self, collection_name, path, flat_paths, params,
               enable_uri_parsing):
    self.collection_name = collection_name
    self.path = path
    self.flat_paths = flat_paths
    self.params = params
    self.enable_uri_parsing = enable_uri_parsing
