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
"""Database Migration Service conversion workspaces composite client."""

from googlecloudsdk.api_lib.database_migration.conversion_workspaces import conversion_workspaces_ai_client
from googlecloudsdk.api_lib.database_migration.conversion_workspaces import conversion_workspaces_crud_client
from googlecloudsdk.api_lib.database_migration.conversion_workspaces import conversion_workspaces_entities_client
from googlecloudsdk.api_lib.database_migration.conversion_workspaces import conversion_workspaces_lro_client
from googlecloudsdk.api_lib.database_migration.conversion_workspaces import conversion_workspaces_operations_client
from googlecloudsdk.calliope import base


class ConversionWorkspacesClient:
  """Composite client for Conversion Workspaces API.

  Attributes:
    ai: The client for the conversion workspaces AI APIs.
    crud: The client for the conversion workspaces CRUD APIs.
    operations: The client for the conversion workspaces operations APIs.
    entities: The client for the conversion workspaces entities APIs.
    lro: The client for the conversion workspaces LRO APIs.
  """

  def __init__(self, release_track: base.ReleaseTrack):
    """Initializes the conversion workspaces client.

    Args:
      release_track: The release track of the client, controlling the API
        version to use.
    """
    self.ai = conversion_workspaces_ai_client.ConversionWorkspacesAIClient(
        parent_client=self,
        release_track=release_track,
    )

    self.crud = (
        conversion_workspaces_crud_client.ConversionWorkspacesCRUDClient(
            parent_client=self,
            release_track=release_track,
        )
    )

    self.operations = conversion_workspaces_operations_client.ConversionWorkspacesOperationsClient(
        parent_client=self,
        release_track=release_track,
    )

    self.entities = conversion_workspaces_entities_client.ConversionWorkspacesEntitiesClient(
        parent_client=self,
        release_track=release_track,
    )

    self.lro = conversion_workspaces_lro_client.ConversionWorkspacesLROClient(
        parent_client=self,
        release_track=release_track,
    )
