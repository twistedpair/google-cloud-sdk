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
"""Database Migration Service conversion workspaces EntityName."""
import dataclasses
from typing import Optional


@dataclasses.dataclass(frozen=True)
class EntityName:
  """Database entity name.

  As entities are defined in an hierarchical structure, their names are can be
  considered as a path.

  The full name is the concatenation of the entire chain of names.
  For example, a table name might be "schema_name.table_name".
  The short name is the last part of the name, in this case "table_name".
  """
  parent_entity_name: Optional['EntityName']
  entity_name: str

  @property
  def full_name(self) -> str:
    """The full name of the entity.

    The name parts are concatenated with a dot.

    Returns:
      The full name of the entity.
    """
    if self.parent_entity_name is None:
      return self.entity_name

    parent_name_full_name = self.parent_entity_name.full_name
    if parent_name_full_name:
      return f'{parent_name_full_name}.{self.entity_name}'
    return self.entity_name

  @property
  def short_name(self) -> str:
    """The short name of the entity."""
    return self.entity_name
