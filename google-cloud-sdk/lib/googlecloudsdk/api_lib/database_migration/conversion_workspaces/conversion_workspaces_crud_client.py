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

from typing import Optional, Tuple

from googlecloudsdk.api_lib.database_migration import api_util
from googlecloudsdk.api_lib.database_migration.conversion_workspaces import base_conversion_workspaces_client
from googlecloudsdk.api_lib.database_migration.conversion_workspaces import conversion_workspace_builder


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
      source_database_engine: str,
      source_database_version: str,
      destination_database_engine: str,
      destination_database_version: str,
      global_settings,
  ):
    """Creates a conversion workspace.

    Args:
      parent_ref: a Resource reference to a parent
        datamigration.projects.locations resource for this conversion workspace.
      conversion_workspace_id: str, the name of the resource to create.
      display_name: str, the display name for the conversion workspace.
      source_database_engine: str, the source database engine for the conversion
        workspace.
      source_database_version: str, the source database version for the
        conversion workspace.
      destination_database_engine: str, the destination database engine for the
        conversion workspace.
      destination_database_version: str, the destination database version for
        the conversion workspace.
      global_settings: GlobalSettings, the global settings for the conversion
        workspace.

    Returns:
      Operation: the operation for creating the conversion workspace.
    """
    return self.cw_service.Create(
        self.messages.DatamigrationProjectsLocationsConversionWorkspacesCreateRequest(
            conversionWorkspace=self.cw_builder.Build(
                display_name=display_name,
                source_database_engine=source_database_engine,
                source_database_version=source_database_version,
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

  def Update(self, name: str, display_name: Optional[str]):
    """Updates a conversion workspace.

    Args:
      name: str, the reference of the conversion workspace to update.
      display_name: Optional[str], the display name to update.

    Returns:
      Operation: the operation for updating the conversion workspace.
    """
    conversion_workspace, update_fields = self._GetUpdatedConversionWorkspace(
        conversion_workspace=self.Read(name),
        display_name=display_name,
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
  ) -> Tuple[str, Tuple[str, ...]]:
    """Returns updated conversion workspace and list of updated fields.

    Args:
      conversion_workspace: str, the conversion workspace to update.
      display_name: str, the display name to update.

    Returns:
      conversion_workspace: str, the updated conversion workspace object.
      update_fields: tuple[str, ...], the list of updated fields.
    """
    update_fields = {}
    if display_name:
      update_fields['displayName'] = display_name

    for field_name, field_value in update_fields.items():
      setattr(conversion_workspace, field_name, field_value)

    return conversion_workspace, update_fields
