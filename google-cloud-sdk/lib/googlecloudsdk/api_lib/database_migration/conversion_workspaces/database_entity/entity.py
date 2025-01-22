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
"""Database Migration Service conversion workspaces Entity."""
import functools
import itertools
from typing import Any, Optional, Sequence

from googlecloudsdk.api_lib.database_migration.conversion_workspaces.database_entity import entity_identifier
from googlecloudsdk.api_lib.database_migration.conversion_workspaces.database_entity import entity_name
from googlecloudsdk.api_lib.database_migration.conversion_workspaces.database_entity import entity_status
from googlecloudsdk.generated_clients.apis.datamigration.v1 import datamigration_v1_messages as messages


class Entity:
  """Object representing a database entity and sub-entities.

  Entity holds the entity's identifier, proto, issues, mappings, and
  sub-entities, which are Entity objects themselves.

  Attributes:
    entity_id: The EntityIdentifier for the entity.
    entity_proto: The proto of the entity.
    issues: The issues related to the entity.
    mappings: The mappings related to the entity.
    sub_entities: The sub-entities of the entity.
  """

  def __init__(
      self,
      entity_id: entity_identifier.EntityIdentifier,
      entity_proto: Any,
      issues: Sequence[messages.EntityIssue],
      mappings: Sequence[messages.EntityMapping],
      sub_entities: Sequence["Entity"],
  ):
    """Initializes the DatabaseEntity.

    Args:
      entity_id: The EntityIdentifier for the entity.
      entity_proto: The proto of the entity.
      issues: The issues related to the entity.
      mappings: The mappings related to the entity.
      sub_entities: The sub-entities of the entity.
    """
    self.entity_id = entity_id
    self.entity_proto = entity_proto
    self.issues = issues
    self.mappings = mappings
    self.sub_entities = sub_entities

  @property
  def name(self) -> entity_name.EntityName:
    """The name object of the entity."""
    return self.entity_id.entity_name

  @property
  def parent_name(self) -> Optional[entity_name.EntityName]:
    """The parent entity name object, if exists."""
    return self.name.parent_entity_name

  @property
  def entity_type(self) -> str:
    """The type of the entity."""
    return self.entity_id.entity_type

  @property
  def tree_type(self) -> str:
    """The tree type of the entity."""
    return self.entity_id.tree_type

  @property
  def display_status(self) -> str:
    """The display status of the entity.

    This status is the one that is exposed to the user.
    It is determined by the entity status, and whether it was manually modified.

    Returns:
      The display status of the entity.
    """
    if self.is_manually_modified:
      return entity_status.EntityStatus.MODIFIED.name
    return self.status_from_issues.name

  @functools.cached_property
  def status_from_issues(self) -> entity_status.EntityStatus:
    """Calculates the entity status based on the issues related to it.

    The status is determined by the highest severity issue found for the
    entity, and its sub-entities.

    The status might not be the one that is exposed to the user, as the
    entity might be manually modified.
    We do not include the modified status here, as that would affect the parent
    as well when it shouldn't, as it might not be modified.

    Returns:
      The entity status.
    """
    return max(
        # Transform the issues to entity statuses.
        itertools.chain(
            # Collect from the issues of the entity.
            map(entity_status.EntityStatus.FromIssue, self.issues),
            # Collect from the sub-entities statuses.
            map(
                lambda sub_entity: sub_entity.status_from_issues,
                self.sub_entities,
            ),
            # Fallback to no issues only if:
            # 1. no entity issues.
            # 2. no sub-entities.
            [entity_status.EntityStatus.NO_ISSUES],
        ),
    )

  @functools.cached_property
  def is_manually_modified(self) -> bool:
    """Was the entity manually modified by the user.

    The entity is considered manually modified if it has a mapping with
    a comment that is the string "Manually converted.".

    Returns:
      True if the entity was manually modified, False otherwise.
    """
    for mapping in self.mappings:
      for mapping_log in mapping.mappingLog:
        if mapping_log.mappingComment == "Manually converted.":
          return True
    return False
