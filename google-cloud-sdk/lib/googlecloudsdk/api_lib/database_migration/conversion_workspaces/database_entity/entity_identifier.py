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
"""Database Migration Service conversion workspaces Entity Identifier."""
import dataclasses

from googlecloudsdk.api_lib.database_migration.conversion_workspaces.database_entity import entity_name
from googlecloudsdk.api_lib.database_migration.conversion_workspaces.database_entity import string_utils
from googlecloudsdk.generated_clients.apis.datamigration.v1 import datamigration_v1_messages as messages


@dataclasses.dataclass(frozen=True)
class EntityIdentifier:
  """Identifier for a database entity and its sub-entities.

  Attributes:
    entity_type: The type of the entity.
    entity_name: The name of the entity, with references to its parent entities.
    tree_type: The tree type of the entity (SOURCE/DRAFT).
  """

  entity_type: str
  entity_name: "entity_name.EntityName"
  tree_type: str

  @classmethod
  def FromEntityDdl(
      cls,
      entity_ddl: messages.EntityDdl,
      parent_entity_identifier: "EntityIdentifier",
  ) -> "EntityIdentifier":
    """Builds an entity identifier for the given entity DDL.

    Args:
      entity_ddl: The entity DDL proto.
      parent_entity_identifier: The parent entity identifier.

    Returns:
      The entity identifier for the given entity DDL.
    """
    return cls(
        entity_type=str(entity_ddl.entityType),
        entity_name=cls._BuildEntityNameFromParent(
            name=entity_ddl.entity,
            parent_entity_name=parent_entity_identifier.entity_name,
        ),
        tree_type=parent_entity_identifier.tree_type,
    )

  @classmethod
  def FromEntityMapping(
      cls,
      entity_mapping: messages.EntityMapping,
      parent_entity_identifier: "EntityIdentifier",
  ) -> "EntityIdentifier":
    """Builds an entity identifier for the given entity mapping.

    Args:
      entity_mapping: The entity Mapping proto.
      parent_entity_identifier: The parent entity identifier.

    Returns:
      The entity identifier for the given entity Mapping.
    """
    if parent_entity_identifier.tree_type == "SOURCE":
      name = entity_mapping.sourceEntity
      entity_type = str(entity_mapping.sourceType)
    else:
      name = entity_mapping.draftEntity
      entity_type = str(entity_mapping.draftType)

    return cls(
        entity_type=entity_type,
        entity_name=cls._BuildEntityNameFromParent(
            name=name,
            parent_entity_name=parent_entity_identifier.entity_name,
        ),
        tree_type=parent_entity_identifier.tree_type,
    )

  @classmethod
  def _BuildEntityNameFromParent(
      cls,
      name: str,
      parent_entity_name: "entity_name.EntityName",
  ) -> "entity_name.EntityName":
    """Builds the entity name from the parent entity name.

    If the name is the same as the parent entity name, then there is no
    additional nesting, and the parent entity name is returned.

    name is allowed to be a short name or a full name, and is split based on the
    parent entity name.

    When the name is a short name, it is assumed to be nested directly under
    the parent entity.

    In order to support period in the name, extracting the short name is done
    by removing the parent name from the name.

    Args:
      name: The name of the entity.
      parent_entity_name: The parent entity name.

    Returns:
      The entity name.
    """
    if name == parent_entity_name.full_name:
      # The names are the same, so it is the same entity.
      return parent_entity_name

    return entity_name.EntityName(
        # Remove the parent from the name, as it might be a full name.
        entity_name=string_utils.RemovePrefix(
            value=name,
            prefix=f"{parent_entity_name.full_name}.",
        ),
        parent_entity_name=parent_entity_name,
    )
