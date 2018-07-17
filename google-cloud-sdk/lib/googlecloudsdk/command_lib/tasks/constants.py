# -*- coding: utf-8 -*- #
# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Constants for `gcloud tasks` commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.app import region_util


PROJECTS_COLLECTION = 'cloudtasks.projects'
LOCATIONS_COLLECTION = 'cloudtasks.projects.locations'
QUEUES_COLLECTION = 'cloudtasks.projects.locations.queues'
TASKS_COLLECTION = 'cloudtasks.projects.locations.queues.tasks'

# TODO(b/33038795): App Engine apps are currently being created with
# multi-regional locations. Remove this map when this is no longer the case.
CLOUD_MULTIREGION_TO_REGION_MAP = {
    'us-central': 'us-central1',
    'europe-west': 'europe-west1',
}
VALID_REGIONS = [
    region_util.Region('us-central', True, True),
    region_util.Region('europe-west', True, True),
    region_util.Region('asia-northeast1', True, True)
]

PULL_QUEUE = 'pull'
APP_ENGINE_QUEUE = 'app-engine'
VALID_QUEUE_TYPES = [PULL_QUEUE, APP_ENGINE_QUEUE]

APP_ENGINE_ROUTING_KEYS = ['service', 'version', 'instance']

QUEUE_MANAGEMENT_WARNING = (
    'You are managing queues with gcloud, do not use queue.yaml or queue.xml '
    'in the future. More details at: '
    'https://cloud.google.com/cloud-tasks/docs/queue-yaml.')
