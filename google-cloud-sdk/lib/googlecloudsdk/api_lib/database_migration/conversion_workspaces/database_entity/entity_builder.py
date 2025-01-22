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
"""Database Migration Service conversion workspaces EntityBuilder."""
from typing import Any, Optional, Sequence

from googlecloudsdk.api_lib.database_migration.conversion_workspaces.database_entity import entity
from googlecloudsdk.api_lib.database_migration.conversion_workspaces.database_entity import entity_identifier
from googlecloudsdk.api_lib.database_migration.conversion_workspaces.database_entity import entity_name
from googlecloudsdk.api_lib.database_migration.conversion_workspaces.database_entity import issue_splitter
from googlecloudsdk.api_lib.database_migration.conversion_workspaces.database_entity import proto_collections
from googlecloudsdk.generated_clients.apis.datamigration.v1 import datamigration_v1_messages as messages


class EntityBuilder:
  """Build Entity objects from a database entity proto."""

  _FIELD_NAME_TO_ENTITY_TYPE = {
      'constraints': 'DATABASE_ENTITY_TYPE_CONSTRAINT',
      'indices': 'DATABASE_ENTITY_TYPE_INDEX',
      'triggers': 'DATABASE_ENTITY_TYPE_TRIGGER',
  }

  def __init__(self, database_entity_proto: messages.DatabaseEntity):
    """Initializes the EntityBuilder.

    The entity and its sub-entities are built from the database entity proto,
    which holds its own details, as well as it's sub-entities' details.

    Args:
      database_entity_proto: The database entity proto.
    """
    self._database_entity_proto = database_entity_proto
    self._issue_splitter = issue_splitter.IssueSplitter(
        issues=self._database_entity_proto.issues,
    )

    self._ddls_collection = proto_collections.BuildEntityDdlCollection(
        database_entity_proto=self._database_entity_proto,
        base_entity_identifier=self.GetDatabaseEntityId(),
    )

    self._mappings_collection = proto_collections.BuildEntityMappingsCollection(
        database_entity_proto=self._database_entity_proto,
        base_entity_identifier=self.GetDatabaseEntityId(),
    )

  def Build(self) -> entity.Entity:
    """Returns a Entity build from the Entity proto."""
    sub_entities = self._GetSubEntities()
    # All issues not collected by sub-entities are considered part of
    # the top-level entity.
    top_level_issues = self._issue_splitter.GetCurrentIssues()
    return entity.Entity(
        entity_id=self.GetDatabaseEntityId(),
        entity_proto=self._database_entity_proto,
        # All issues not collected by sub-entities are considered part of
        # the top-level entity.
        issues=top_level_issues,
        mappings=self._mappings_collection.get(self.GetDatabaseEntityId(), []),
        sub_entities=sub_entities,
    )

  def GetParentEntityName(self) -> Optional[entity_name.EntityName]:
    """Returns the parent entity name.

    Parent entity name might be None for top-most entities (i.e. schemas).

    Returns:
      The parent entity name, or None if the entity has no parent.
    """
    if not self._database_entity_proto.parentEntity:
      return None
    return entity_name.EntityName(
        parent_entity_name=None,
        entity_name=self._database_entity_proto.parentEntity,
    )

  def GetDatabaseEntityName(self) -> entity_name.EntityName:
    """The name object of the entity."""
    return entity_name.EntityName(
        parent_entity_name=self.GetParentEntityName(),
        entity_name=self._database_entity_proto.shortName,
    )

  def GetDatabaseEntityType(self) -> str:
    """The type of the entity."""
    return str(self._database_entity_proto.entityType)

  def GetDatabaseEntityId(self) -> entity_identifier.EntityIdentifier:
    """The identifier of the entity."""
    return entity_identifier.EntityIdentifier(
        entity_type=self.GetDatabaseEntityType(),
        entity_name=self.GetDatabaseEntityName(),
        tree_type=self.GetTreeType(),
    )

  def GetTreeType(self) -> str:
    """Returns the tree type of the entity."""
    return str(self._database_entity_proto.tree)

  def _GetSubEntities(self) -> Sequence[entity.Entity]:
    """Identifiers for the sub-entities of the database entity.

    Sub-entities are entities that are nested under the database entity.
    For example, a table entity might have constraints, indices, and triggers
    as sub-entities.

    Returns:
      The sub-entities of the database entity.
    """
    # Each type has a different field in the proto for its type-specific data.
    sub_entities = []

    detailed_proto = self._GetDetailedProto()
    if detailed_proto is None:
      return sub_entities

    for field_name, entity_type in self._FIELD_NAME_TO_ENTITY_TYPE.items():
      for sub_entity in getattr(detailed_proto, field_name, []):
        sub_entities.append(self._BuildSubEntity(entity_type, sub_entity))
    return sub_entities

  def _GetDetailedProto(self) -> Optional[Any]:
    """Returns the field holding the details for the entity, based on its type."""
    entity_type = self.GetDatabaseEntityId().entity_type
    if entity_type == 'DATABASE_ENTITY_TYPE_TABLE':
      return self._database_entity_proto.table
    if entity_type == 'DATABASE_ENTITY_TYPE_VIEW':
      return self._database_entity_proto.view
    if entity_type == 'DATABASE_ENTITY_TYPE_MATERIALIZED_VIEW':
      return self._database_entity_proto.materializedView
    return None

  def _BuildSubEntity(
      self,
      entity_type: str,
      sub_entity_proto: Any,
  ) -> entity.Entity:
    """Builds the sub-entity nested under the database entity.

    Args:
      entity_type: The type of the sub-entity.
      sub_entity_proto: The proto of the sub-entity.

    Returns:
      The Entity object of the sub-entity.
    """
    sub_entity_id = entity_identifier.EntityIdentifier(
        entity_type=entity_type,
        entity_name=entity_name.EntityName(
            parent_entity_name=self.GetDatabaseEntityName(),
            entity_name=sub_entity_proto.name,
        ),
        tree_type=self.GetTreeType(),
    )
    sub_entity_ddl = self._ddls_collection.get(sub_entity_id, None)
    sub_entity_issues = self._issue_splitter.ExtractIssues(
        issue_ids=sub_entity_ddl.issueId if sub_entity_ddl else [],
    )
    return entity.Entity(
        entity_id=sub_entity_id,
        entity_proto=sub_entity_proto,
        issues=sub_entity_issues,
        mappings=self._mappings_collection.get(sub_entity_id, []),
        sub_entities=[],
    )
