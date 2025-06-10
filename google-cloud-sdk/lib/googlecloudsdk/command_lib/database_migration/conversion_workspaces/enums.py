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
"""Enums for the conversion workspace related commands."""

import enum
from typing import Any, List, Set


class StrEnum(str, enum.Enum):
  """Base class for enums that are also strings."""

  @staticmethod
  def _generate_next_value_(
      name: str,
      start: int,
      count: int,
      last_values: List[Any],
  ) -> str:
    return name

  def __str__(self) -> str:
    return self.value


class SourceDatabaseProvider(StrEnum):
  """Source database provider."""

  AMAZON_RDS = enum.auto()
  AZURE_MANAGED_INSTANCE = enum.auto()
  AZURE_SQL_DATABASE = enum.auto()
  CLOUDSQL = enum.auto()
  UNSPECIFIED = enum.auto()


class DestinationDatabaseProvider(StrEnum):
  """Destination database provider."""

  ALLOYDB = enum.auto()
  CLOUDSQL = enum.auto()


class SourceDatabaseEngine(StrEnum):
  """Source database engine type."""

  ORACLE = enum.auto()
  SQL_SERVER = enum.auto()

  @property
  def supported_providers(self) -> Set[SourceDatabaseProvider]:
    if self == self.ORACLE:
      return {
          SourceDatabaseProvider.UNSPECIFIED,
      }

    if self == self.SQL_SERVER:
      return {
          SourceDatabaseProvider.AMAZON_RDS,
          SourceDatabaseProvider.AZURE_MANAGED_INSTANCE,
          SourceDatabaseProvider.AZURE_SQL_DATABASE,
          SourceDatabaseProvider.CLOUDSQL,
          SourceDatabaseProvider.UNSPECIFIED,
      }

    return set()


class DestinationDatabaseEngine(StrEnum):
  """Destination database engine type."""

  POSTGRESQL = enum.auto()

  @property
  def supported_providers(self) -> Set[DestinationDatabaseProvider]:
    if self == self.POSTGRESQL:
      return {
          DestinationDatabaseProvider.ALLOYDB,
          DestinationDatabaseProvider.CLOUDSQL,
      }

    return set()
