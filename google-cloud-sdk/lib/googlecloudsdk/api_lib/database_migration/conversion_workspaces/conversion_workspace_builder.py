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

from googlecloudsdk.api_lib.database_migration import api_util
from googlecloudsdk.calliope import base


class ConversionWorkspaceBuilder:
  """Builder for ConversionWorkspace message objects."""

  def __init__(self, release_track: base.ReleaseTrack):
    self.messages = api_util.GetMessagesModule(release_track)

  def Build(
      self,
      display_name: str,
      source_database_engine: str,
      source_database_version: str,
      destination_database_engine: str,
      destination_database_version: str,
      global_settings,
  ):
    """Returns a conversion workspace.

    Args:
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
      A ConversionWorkspace message object.
    """

    return self.messages.ConversionWorkspace(
        globalSettings=global_settings,
        displayName=display_name,
        source=self._GetDatabaseEngineInfo(
            database_engine=source_database_engine,
            database_version=source_database_version,
        ),
        destination=self._GetDatabaseEngineInfo(
            database_engine=destination_database_engine,
            database_version=destination_database_version,
        ),
    )

  def _GetDatabaseEngineInfo(
      self,
      database_engine: str,
      database_version: str,
  ):
    """Returns a DatabaseEngineInfo message object.

    Args:
      database_engine: str, the database engine for the conversion workspace.
      database_version: str, the database version for the conversion workspace.

    Returns:
      A DatabaseEngineInfo message object.
    """
    return self.messages.DatabaseEngineInfo(
        engine=self._GetDatabaseEngine(database_engine=database_engine),
        version=database_version,
    )

  def _GetDatabaseEngine(self, database_engine: str):
    """Returns a EngineValue enum value.

    Args:
      database_engine: str, the database engine for the conversion workspace.

    Returns:
      An EngineValue enum value.
    """
    return (
        self.messages.DatabaseEngineInfo.EngineValueValuesEnum.lookup_by_name(
            database_engine,
        )
    )
