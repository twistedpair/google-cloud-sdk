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
"""Database Migration Service conversion workspaces Entity serializers."""
from typing import Any, Dict, Iterable, Optional, Sequence

from googlecloudsdk.api_lib.database_migration.conversion_workspaces.database_entity import entity
from googlecloudsdk.api_lib.database_migration.conversion_workspaces.database_entity import string_utils
from googlecloudsdk.generated_clients.apis.datamigration.v1 import datamigration_v1_messages as messages


def GetSummaries(entity_obj: entity.Entity) -> Iterable[Dict[str, Any]]:
  """Yields the entity and its sub-entities.

  Args:
    entity_obj: The entity to serialize.

  Yields:
    Serialized entities.
  """
  yield {
      "shortName": entity_obj.name.short_name,
      "parentEntity": (
          entity_obj.parent_name.full_name if entity_obj.parent_name else ""
      ),
      "entityType": string_utils.RemovePrefix(
          value=entity_obj.entity_type,
          prefix="DATABASE_ENTITY_TYPE_",
      ),
      "tree": entity_obj.entity_id.tree_type,
      "status": entity_obj.display_status,
  }

  # Serialize sub-entities recursively.
  for sub_entity in entity_obj.sub_entities:
    yield from GetSummaries(sub_entity)


def GetDdls(entity_obj: entity.Entity) -> Iterable[messages.EntityDdl]:
  """Yields the DDLs protos for the given entity and its sub-entities.

  Args:
    entity_obj: The entity to serialize DDLs for.
  """
  for entity_ddl in entity_obj.entity_proto.entityDdl:
    yield entity_ddl


def GetIssues(
    entity_obj: entity.Entity,
    issue_severities: Optional[
        Sequence[messages.EntityIssue.SeverityValueValuesEnum]
    ] = None,
) -> Iterable[Dict[str, Any]]:
  """Yields the issues for the given entity and its sub-entities.

  Args:
    entity_obj: The entity to serialize issues for.
    issue_severities: The issue severities to return.

  Yields:
    Serialized issues.
  """
  should_include_issue = lambda issue: (
      issue_severities is None or issue.severity in issue_severities
  )

  for issue in entity_obj.issues:
    if not should_include_issue(issue):
      continue

    yield {
        "parentEntity": (
            entity_obj.parent_name.full_name if entity_obj.parent_name else ""
        ),
        "shortName": entity_obj.name.short_name,
        "entityType": string_utils.RemovePrefix(
            value=entity_obj.entity_type,
            prefix="DATABASE_ENTITY_TYPE_",
        ),
        "issueId": issue.id,
        "issueType": string_utils.RemovePrefix(
            value=str(issue.type),
            prefix="ISSUE_TYPE_",
        ),
        "issueSeverity": string_utils.RemovePrefix(
            value=str(issue.severity),
            prefix="ISSUE_SEVERITY_",
        ),
        "issueCode": issue.code,
        "issueMessage": issue.message,
    }

  # Serialize issues from sub-entities recursively.
  for sub_entity in entity_obj.sub_entities:
    yield from GetIssues(
        entity_obj=sub_entity,
        issue_severities=issue_severities,
    )
