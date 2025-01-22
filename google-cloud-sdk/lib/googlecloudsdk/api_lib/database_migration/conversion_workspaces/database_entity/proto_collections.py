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
"""Database Migration Service conversion workspaces Proto Collections."""
import collections
from typing import Mapping, Sequence

from googlecloudsdk.api_lib.database_migration.conversion_workspaces.database_entity import entity_identifier
from googlecloudsdk.generated_clients.apis.datamigration.v1 import datamigration_v1_messages as messages


def BuildEntityDdlCollection(
    database_entity_proto: messages.DatabaseEntity,
    base_entity_identifier: entity_identifier.EntityIdentifier,
) -> Mapping[entity_identifier.EntityIdentifier, messages.EntityDdl]:
  """Builds a mapping between entity identifier and entity DDL.

  The entity names are split based on the base entity identifier.
  All DDLs are considered to be part of the base entity or its direct
  children.

  Args:
    database_entity_proto: The database entity proto.
    base_entity_identifier: The base entity identifier.

  Returns:
    The mapping between entity identifier and entity DDL.
  """
  return {
      entity_identifier.EntityIdentifier.FromEntityDdl(
          entity_ddl=entity_ddl,
          parent_entity_identifier=base_entity_identifier,
      ): entity_ddl
      for entity_ddl in database_entity_proto.entityDdl
  }


def BuildEntityMappingsCollection(
    database_entity_proto: messages.DatabaseEntity,
    base_entity_identifier: entity_identifier.EntityIdentifier,
) -> Mapping[
    entity_identifier.EntityIdentifier, Sequence[messages.EntityMapping]
]:
  """Builds a mapping between entity identifier and entity mappings.

  The entity names are split based on the base entity identifier.
  All mappings are considered to be part of the base entity or its direct
  children.

  Args:
    database_entity_proto: The database entity proto.
    base_entity_identifier: The base entity identifier.

  Returns:
    The entity mapping protos for the given entity.
  """
  entity_id_to_entity_mappings = collections.defaultdict(list)
  for entity_mapping in database_entity_proto.mappings:
    entity_id = entity_identifier.EntityIdentifier.FromEntityMapping(
        entity_mapping=entity_mapping,
        parent_entity_identifier=base_entity_identifier,
    )
    entity_id_to_entity_mappings[entity_id].append(entity_mapping)

  return entity_id_to_entity_mappings
