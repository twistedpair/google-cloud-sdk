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
"""Database Migration Service conversion workspaces AI APIs."""

from googlecloudsdk.api_lib.database_migration.conversion_workspaces import base_conversion_workspaces_client
from googlecloudsdk.generated_clients.apis.datamigration.v1 import datamigration_v1_messages as messages


class ConversionWorkspacesAIClient(
    base_conversion_workspaces_client.BaseConversionWorkspacesClient
):
  """Client for Conversion Workspaces AI APIs."""

  def ConvertApplicationCode(
      self,
      name: str,
      source_code: str,
  ) -> messages.ConvertApplicationCodeResponse:
    """Converts application code using AI.

    This method converts application code containing SQL statements, to
    PostgreSQL dialect, using AI.

    Args:
      name: the name of the conversion workspace.
      source_code: the source code to be converted.

    Returns:
      The response from the API.
    """
    return self.location_service.ConvertApplicationCode(
        self.messages.DatamigrationProjectsLocationsConvertApplicationCodeRequest(
            name=name,
            convertApplicationCodeRequest=self.messages.ConvertApplicationCodeRequest(
                sourceCode=source_code,
            ),
        ),
    )
