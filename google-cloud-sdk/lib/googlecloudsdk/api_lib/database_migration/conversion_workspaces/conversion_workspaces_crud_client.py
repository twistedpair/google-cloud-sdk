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
"""Database Migration Service conversion workspaces CRUD API."""

from typing import Optional, Set, Tuple

from googlecloudsdk.api_lib.database_migration import api_util
from googlecloudsdk.api_lib.database_migration.conversion_workspaces import base_conversion_workspaces_client
from googlecloudsdk.api_lib.database_migration.conversion_workspaces import conversion_workspace_builder
from googlecloudsdk.command_lib.database_migration.conversion_workspaces import enums
from googlecloudsdk.generated_clients.apis.datamigration.v1 import datamigration_v1_messages as messages


class ConversionWorkspacesCRUDClient(
    base_conversion_workspaces_client.BaseConversionWorkspacesClient
):
  """Client for Conversion Workspaces CRUD API."""

  @property
  def cw_builder(
      self,
  ) -> conversion_workspace_builder.ConversionWorkspaceBuilder:
    """Returns an instance of the conversion workspace builder."""
    return conversion_workspace_builder.ConversionWorkspaceBuilder(
        release_track=self.release_track,
    )

  def Create(
      self,
      parent_ref: str,
      conversion_workspace_id: str,
      display_name: str,
      source_database_provider: enums.SourceDatabaseProvider,
      source_database_engine: enums.SourceDatabaseEngine,
      source_database_version: str,
      destination_database_provider: enums.DestinationDatabaseProvider,
      destination_database_engine: enums.DestinationDatabaseEngine,
      destination_database_version: str,
      global_settings: messages.ConversionWorkspace.GlobalSettingsValue,
  ) -> messages.Operation:
    """Creates a conversion workspace.

    Args:
      parent_ref: a Resource reference to a parent
        datamigration.projects.locations resource for this conversion workspace.
      conversion_workspace_id: the name of the resource to create.
      display_name: the display name for the conversion workspace.
      source_database_provider: the source database provider for the conversion
        workspace.
      source_database_engine: the source database engine for the conversion
        workspace.
      source_database_version: the source database version for the conversion
        workspace.
      destination_database_provider: the destination database provider for the
        conversion workspace.
      destination_database_engine: the destination database engine for the
        conversion workspace.
      destination_database_version: the destination database version for the
        conversion workspace.
      global_settings: GlobalSettings, the global settings for the conversion
        workspace.

    Returns:
      Operation: the operation for creating the conversion workspace.
    """
    return self.cw_service.Create(
        self.messages.DatamigrationProjectsLocationsConversionWorkspacesCreateRequest(
            conversionWorkspace=self.cw_builder.Build(
                display_name=display_name,
                source_database_provider=source_database_provider,
                source_database_engine=source_database_engine,
                source_database_version=source_database_version,
                destination_database_provider=destination_database_provider,
                destination_database_engine=destination_database_engine,
                destination_database_version=destination_database_version,
                global_settings=global_settings,
            ),
            conversionWorkspaceId=conversion_workspace_id,
            parent=parent_ref,
            requestId=api_util.GenerateRequestId(),
        ),
    )

  def Read(self, name: str):
    return self.cw_service.Get(
        self.messages.DatamigrationProjectsLocationsConversionWorkspacesGetRequest(
            name=name,
        )
    )

  def Update(
      self,
      name: str,
      display_name: Optional[str],
      global_filter: Optional[str],
  ):
    """Updates a conversion workspace.

    Args:
      name: str, the reference of the conversion workspace to update.
      display_name: the display name to update.
      global_filter: the global filter for the conversion workspace.

    Returns:
      Operation: the operation for updating the conversion workspace.
    """
    conversion_workspace, update_fields = self._GetUpdatedConversionWorkspace(
        conversion_workspace=self.Read(name),
        display_name=display_name,
        global_filter=global_filter,
    )
    return self.cw_service.Patch(
        self.messages.DatamigrationProjectsLocationsConversionWorkspacesPatchRequest(
            conversionWorkspace=conversion_workspace,
            name=name,
            requestId=api_util.GenerateRequestId(),
            updateMask=','.join(update_fields),
        ),
    )

  def Delete(self, name: str):
    """Deletes a conversion workspace.

    Args:
      name: str, the name of the resource to delete.

    Returns:
      Operation: the operation for deleting the conversion workspace.
    """
    return self.cw_service.Delete(
        self.messages.DatamigrationProjectsLocationsConversionWorkspacesDeleteRequest(
            name=name,
            requestId=api_util.GenerateRequestId(),
        ),
    )

  def _GetUpdatedConversionWorkspace(
      self,
      conversion_workspace: str,
      display_name: Optional[str],
      global_filter: Optional[str],
  ) -> Tuple[str, Set[str]]:
    """Returns updated conversion workspace and list of updated fields.

    Args:
      conversion_workspace: the conversion workspace to update.
      display_name: the display name to update.
      global_filter: the global filter for the conversion workspace.

    Returns:
      conversion_workspace: str, the updated conversion workspace object.
      update_fields: tuple[str, ...], the list of updated fields.
    """
    update_fields = set()

    if display_name:
      conversion_workspace.displayName = display_name
      update_fields.add('displayName')

    if global_filter is not None:
      conversion_workspace.globalSettings = self.messages.ConversionWorkspace.GlobalSettingsValue(
          additionalProperties=[
              self.messages.ConversionWorkspace.GlobalSettingsValue.AdditionalProperty(
                  key='filter',
                  value=global_filter,
              ),
          ]
      )
      update_fields.add('globalSettings.filter')

    return conversion_workspace, update_fields
