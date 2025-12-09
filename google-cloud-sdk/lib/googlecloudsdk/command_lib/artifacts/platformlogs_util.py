# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Utility functions for platform logs."""

from googlecloudsdk.command_lib.artifacts import util
from googlecloudsdk.core import resources


def _GetClientAndResourceName(args, client):
  """Returns the service client and config resource name.

  Args:
    args: User input args.
    client: The API service client.

  Returns:
    service: The service client for either project or repository level
      operations.
    config_name: The full resource name of the platform logs config.
    is_repository: True if the resource is a repository.
  """
  project = util.GetProject(args)
  location = util.GetLocation(args)

  if args.IsSpecified('repository'):
    repo = util.GetRepo(args)
    resource_ref = resources.REGISTRY.Parse(
        repo,
        params={'projectsId': project, 'locationsId': location},
        collection='artifactregistry.projects.locations.repositories',
    )
    service = client.projects_locations_repositories
    is_repository = True
  else:
    resource_ref = resources.REGISTRY.Parse(
        location,
        params={'projectsId': project},
        collection='artifactregistry.projects.locations',
    )
    service = client.projects_locations
    is_repository = False
  config_name = resource_ref.RelativeName() + '/platformLogsConfig'
  return service, config_name, is_repository


def GetPlatformLogsConfig(args, client, messages):
  """Gets the platform logs config.

  Args:
    args: User input args.
    client: The API service client.
    messages: The API messages module.

  Returns:
    The retrieved platform logs config.
  """
  service, config_name, is_repository = _GetClientAndResourceName(args, client)

  if is_repository:
    request_message = (
        messages.ArtifactregistryProjectsLocationsRepositoriesGetPlatformLogsConfigRequest
    )
  else:
    request_message = (
        messages.ArtifactregistryProjectsLocationsGetPlatformLogsConfigRequest
    )
  request = request_message(name=config_name)
  return service.GetPlatformLogsConfig(request)


def UpdatePlatformLogsConfig(args, client, messages, platform_logs_config):
  """Updates the platform logs config.

  Args:
    args: User input args.
    client: The API service client.
    messages: The API messages module.
    platform_logs_config: The platform logs config to update.

  Returns:
    The updated platform logs config.
  """
  service, config_name, is_repository = _GetClientAndResourceName(args, client)

  if is_repository:
    request_message = (
        messages.ArtifactregistryProjectsLocationsRepositoriesUpdatePlatformLogsConfigRequest
    )
  else:
    request_message = (
        messages.ArtifactregistryProjectsLocationsUpdatePlatformLogsConfigRequest
    )

  platform_logs_config.name = config_name
  request = request_message(
      name=config_name, platformLogsConfig=platform_logs_config
  )
  return service.UpdatePlatformLogsConfig(request)
