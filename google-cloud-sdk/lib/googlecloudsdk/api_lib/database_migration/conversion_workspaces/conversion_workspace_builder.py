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
"""Builder for ConversionWorkspace message objects."""
from typing import Dict

from googlecloudsdk.api_lib.database_migration import api_util
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.database_migration.conversion_workspaces import enums
from googlecloudsdk.generated_clients.apis.datamigration.v1 import datamigration_v1_messages as messages


class ConversionWorkspaceBuilder:
  """Builder for ConversionWorkspace message objects."""

  def __init__(self, release_track: base.ReleaseTrack):
    self.messages = api_util.GetMessagesModule(release_track)

  def Build(
      self,
      display_name: str,
      source_database_provider: enums.SourceDatabaseProvider,
      source_database_engine: enums.SourceDatabaseEngine,
      source_database_version: str,
      destination_database_provider: enums.DestinationDatabaseProvider,
      destination_database_engine: enums.DestinationDatabaseEngine,
      destination_database_version: str,
      global_settings: messages.ConversionWorkspace.GlobalSettingsValue,
  ) -> messages.ConversionWorkspace:
    """Returns a conversion workspace.

    Args:
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
      global_settings: the global settings for the conversion workspace.

    Returns:
      A ConversionWorkspace message object.
    """

    return self.messages.ConversionWorkspace(
        globalSettings=global_settings,
        displayName=display_name,
        source=self.messages.DatabaseEngineInfo(
            engine=self._source_engine_to_engine_mapping.get(
                source_database_engine,
                self.messages.DatabaseEngineInfo.EngineValueValuesEnum.DATABASE_ENGINE_UNSPECIFIED,
            ),
            version=source_database_version,
        ),
        destination=self.messages.DatabaseEngineInfo(
            engine=self._destination_engine_to_engine_mapping.get(
                destination_database_engine,
                self.messages.DatabaseEngineInfo.EngineValueValuesEnum.DATABASE_ENGINE_UNSPECIFIED,
            ),
            version=destination_database_version,
        ),
        sourceProvider=self._source_provider_to_provider_mapping.get(
            source_database_provider,
            self.messages.ConversionWorkspace.SourceProviderValueValuesEnum.DATABASE_PROVIDER_UNSPECIFIED,
        ),
        destinationProvider=self._destination_provider_to_provider_mapping.get(
            destination_database_provider,
            self.messages.ConversionWorkspace.DestinationProviderValueValuesEnum.DATABASE_PROVIDER_UNSPECIFIED,
        ),
    )

  @property
  def _source_engine_to_engine_mapping(
      self,
  ) -> Dict[
      enums.SourceDatabaseEngine,
      messages.DatabaseEngineInfo.EngineValueValuesEnum,
  ]:
    """Returns a mapping from source database engine CLI-enum to engine API-enum."""
    return {
        enums.SourceDatabaseEngine.ORACLE: (
            self.messages.DatabaseEngineInfo.EngineValueValuesEnum.ORACLE
        ),
        enums.SourceDatabaseEngine.SQL_SERVER: (
            self.messages.DatabaseEngineInfo.EngineValueValuesEnum.SQLSERVER
        ),
    }

  @property
  def _destination_engine_to_engine_mapping(
      self,
  ) -> Dict[
      enums.DestinationDatabaseEngine,
      messages.DatabaseEngineInfo.EngineValueValuesEnum,
  ]:
    """Returns a mapping from destination database engine CLI-enum to engine API-enum."""
    return {
        enums.DestinationDatabaseEngine.POSTGRESQL: (
            self.messages.DatabaseEngineInfo.EngineValueValuesEnum.POSTGRESQL
        ),
    }

  @property
  def _source_provider_to_provider_mapping(
      self,
  ) -> Dict[
      enums.SourceDatabaseProvider,
      messages.ConversionWorkspace.SourceProviderValueValuesEnum,
  ]:
    """Returns a mapping from source database provider CLI-enum to provider API-enum."""
    return {
        enums.SourceDatabaseProvider.UNSPECIFIED: (
            self.messages.ConversionWorkspace.SourceProviderValueValuesEnum.DATABASE_PROVIDER_UNSPECIFIED
        ),
        enums.SourceDatabaseProvider.AMAZON_RDS: (
            self.messages.ConversionWorkspace.SourceProviderValueValuesEnum.RDS
        ),
        enums.SourceDatabaseProvider.CLOUDSQL: (
            self.messages.ConversionWorkspace.SourceProviderValueValuesEnum.CLOUDSQL
        ),
        enums.SourceDatabaseProvider.AZURE_MANAGED_INSTANCE: (
            self.messages.ConversionWorkspace.SourceProviderValueValuesEnum.AZURE_MANAGED_INSTANCE
        ),
        enums.SourceDatabaseProvider.AZURE_SQL_DATABASE: (
            self.messages.ConversionWorkspace.SourceProviderValueValuesEnum.AZURE_SQL_DATABASE
        ),
    }

  @property
  def _destination_provider_to_provider_mapping(
      self,
  ) -> Dict[
      enums.DestinationDatabaseProvider,
      messages.ConversionWorkspace.DestinationProviderValueValuesEnum,
  ]:
    """Returns a mapping from destination database provider CLI-enum to provider API-enum."""
    return {
        enums.DestinationDatabaseProvider.CLOUDSQL: (
            self.messages.ConversionWorkspace.DestinationProviderValueValuesEnum.CLOUDSQL
        ),
        enums.DestinationDatabaseProvider.ALLOYDB: (
            self.messages.ConversionWorkspace.DestinationProviderValueValuesEnum.ALLOYDB
        ),
    }
