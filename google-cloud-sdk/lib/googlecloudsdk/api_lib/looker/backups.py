# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Useful commands for interacting with the Looker Backups API."""

from googlecloudsdk.api_lib.looker import utils
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import log

# API version constants
API_VERSION_DEFAULT = 'v1'


def GetClient(release_track):
  """Returns the Looker client for backups."""
  return apis.GetClientInstance('looker', utils.VERSION_MAP[release_track])


def GetService(release_track):
  """Returns the service for interacting with the Backups service."""
  return GetClient(release_track).projects_locations_instances_backups


def GetMessages(release_track):
  """Import and return the appropriate operations messages module."""
  return apis.GetMessagesModule('looker', utils.VERSION_MAP[release_track])


def CreateBackup(parent, release_track):
  """Creates the Backup with the given parent.

  Args:
    parent: the instance where the backup will be created, a string.
    release_track: the release track to use for the API call.

  Returns:
    a long running Operation
  """
  log.status.Print(
      'Creating backup for instance {parent}'.format(parent=parent)
  )
  return GetService(release_track).Create(
      GetMessages(
          release_track
      ).LookerProjectsLocationsInstancesBackupsCreateRequest(parent=parent)
  )
