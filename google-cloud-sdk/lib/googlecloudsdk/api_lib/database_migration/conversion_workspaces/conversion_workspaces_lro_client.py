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
"""Database Migration Service conversion workspaces LRO API."""

from googlecloudsdk.api_lib.database_migration import api_util
from googlecloudsdk.api_lib.database_migration.conversion_workspaces import base_conversion_workspaces_client


class ConversionWorkspacesLROClient(
    base_conversion_workspaces_client.BaseConversionWorkspacesClient
):
  """Client for Conversion Workspaces LRO API."""

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.resource_parser = api_util.GetResourceParser(self.release_track)

  def Read(self, operation, project_id: str, location_id: str):
    """Reads the Conversion Workspace long running operation.

    Args:
      operation: The Conversion Workspace long running operation.
      project_id: The project ID.
      location_id: The location ID.

    Returns:
      The Conversion Workspace long running operation.
    """
    operations_id = self.resource_parser.Create(
        'datamigration.projects.locations.operations',
        operationsId=operation.name,
        projectsId=project_id,
        locationsId=location_id,
    ).operationsId

    return self.client.projects_locations_operations.Get(
        self.messages.DatamigrationProjectsLocationsOperationsGetRequest(
            name=operations_id,
        ),
    )

  def Wait(self, operation, has_resource: bool) -> None:
    """Waits for the Conversion Workspace long running operation to complete.

    Args:
      operation: The Conversion Workspace long running operation.
      has_resource: Whether the operation contaions a resource when done.
    """
    api_util.HandleLRO(
        client=self.client,
        result_operation=operation,
        service=self.cw_service,
        no_resource=not has_resource,
    )
