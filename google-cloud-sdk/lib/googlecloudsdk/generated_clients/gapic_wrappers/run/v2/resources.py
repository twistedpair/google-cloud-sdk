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
"""Resource definitions for Cloud Platform APIs generated from gapic."""

import enum


BASE_URL = 'https://run.googleapis.com/v2/'
DOCS_URL = 'https://cloud.google.com/apis/docs/overview'


class Collections(enum.Enum):
  """Collections for all supported apis."""

  LOCATIONS_POLICY = (
      'locations.policy',
      'locations/{location}/policy',
      {},
      ['location'],
      True
  )
  PROJECTS = (
      'projects',
      'projects/{project}',
      {},
      ['project'],
      True
  )
  PROJECTS_LOCATIONS = (
      'projects.locations',
      'projects/{project}/locations/{location}',
      {},
      ['project', 'location'],
      True
  )
  PROJECTS_LOCATIONS_BUILDS = (
      'projects.locations.builds',
      'projects/{project}/locations/{location}/builds/{build}',
      {},
      ['project', 'location', 'build'],
      True
  )
  PROJECTS_LOCATIONS_CONNECTORS = (
      'projects.locations.connectors',
      'projects/{project}/locations/{location}/connectors/{connector}',
      {},
      ['project', 'location', 'connector'],
      True
  )
  PROJECTS_LOCATIONS_JOBS = (
      'projects.locations.jobs',
      'projects/{project}/locations/{location}/jobs/{job}',
      {},
      ['project', 'location', 'job'],
      True
  )
  PROJECTS_LOCATIONS_JOBS_EXECUTIONS = (
      'projects.locations.jobs.executions',
      'projects/{project}/locations/{location}/jobs/{job}/executions/'
      '{execution}',
      {},
      ['project', 'location', 'job', 'execution'],
      True
  )
  PROJECTS_LOCATIONS_JOBS_EXECUTIONS_TASKS = (
      'projects.locations.jobs.executions.tasks',
      'projects/{project}/locations/{location}/jobs/{job}/executions/'
      '{execution}/tasks/{task}',
      {},
      ['project', 'location', 'job', 'execution', 'task'],
      True
  )
  PROJECTS_LOCATIONS_KEYRINGS = (
      'projects.locations.keyRings',
      'projects/{project}/locations/{location}/keyRings/{key_ring}',
      {},
      ['project', 'location', 'key_ring'],
      True
  )
  PROJECTS_LOCATIONS_KEYRINGS_CRYPTOKEYS = (
      'projects.locations.keyRings.cryptoKeys',
      'projects/{project}/locations/{location}/keyRings/{key_ring}/'
      'cryptoKeys/{crypto_key}',
      {},
      ['project', 'location', 'key_ring', 'crypto_key'],
      True
  )
  PROJECTS_LOCATIONS_MESHES = (
      'projects.locations.meshes',
      'projects/{project}/locations/{location}/meshes/{mesh}',
      {},
      ['project', 'location', 'mesh'],
      True
  )
  PROJECTS_LOCATIONS_SERVICES = (
      'projects.locations.services',
      'projects/{project}/locations/{location}/services/{service}',
      {},
      ['project', 'location', 'service'],
      True
  )
  PROJECTS_LOCATIONS_SERVICES_REVISIONS = (
      'projects.locations.services.revisions',
      'projects/{project}/locations/{location}/services/{service}/revisions/'
      '{revision}',
      {},
      ['project', 'location', 'service', 'revision'],
      True
  )
  PROJECTS_LOCATIONS_WORKERPOOLS = (
      'projects.locations.workerPools',
      'projects/{project}/locations/{location}/workerPools/{worker_pool}',
      {},
      ['project', 'location', 'worker_pool'],
      True
  )
  PROJECTS_POLICY = (
      'projects.policy',
      'projects/{project}/policy',
      {},
      ['project'],
      True
  )
  PROJECTS_SECRETS = (
      'projects.secrets',
      'projects/{project}/secrets/{secret}',
      {},
      ['project', 'secret'],
      True
  )
  PROJECTS_SECRETS_VERSIONS = (
      'projects.secrets.versions',
      'projects/{project}/secrets/{secret}/versions/{version}',
      {},
      ['project', 'secret', 'version'],
      True
  )

  def __init__(self, collection_name, path, flat_paths, params,
               enable_uri_parsing):
    self.collection_name = collection_name
    self.path = path
    self.flat_paths = flat_paths
    self.params = params
    self.enable_uri_parsing = enable_uri_parsing
