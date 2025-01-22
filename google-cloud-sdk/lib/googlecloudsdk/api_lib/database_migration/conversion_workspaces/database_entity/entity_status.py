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
"""Database Migration Service conversion workspaces EntityStatus."""
import enum
import functools
from typing import Any

from googlecloudsdk.generated_clients.apis.datamigration.v1 import datamigration_v1_messages as messages


@functools.total_ordering
class EntityStatus(enum.Enum):
  """Entity status.

  The value of the enum is the severity of the status, where higher value means
  higher severity.

  Attributes:
    NO_ISSUES: No issues found for the entity.
    REVIEW_RECOMMENDED: Issues found for the entity, but they are not
      actionable.
    ACTION_REQUIRED: Issues found for the entity, and they are actionable.
    MODIFIED: The entity was manually modified (should top all other statuses).
  """

  NO_ISSUES = 0
  REVIEW_RECOMMENDED = 1
  ACTION_REQUIRED = 2
  MODIFIED = 3

  @classmethod
  def FromIssue(cls, issue: messages.EntityIssue) -> 'EntityStatus':
    """Determines the entity status from the severity of an issue."""
    return cls.FromIssueSeverity(issue.severity)

  @classmethod
  def FromIssueSeverity(cls, issue_severity: str) -> 'EntityStatus':
    """Detrmines the entity status from the severity string."""
    if str(issue_severity) == 'ISSUE_SEVERITY_ERROR':
      return cls.ACTION_REQUIRED
    if str(issue_severity) == 'ISSUE_SEVERITY_WARNING':
      return cls.REVIEW_RECOMMENDED
    return cls.NO_ISSUES

  def __lt__(self, other: Any) -> bool:
    """Is the entity status less severe than other entity status.

    Args:
      other: The other entity status to compare to.

    Returns:
      True if the entity status is less severe than other entity status.
    """
    if not isinstance(other, EntityStatus):
      raise TypeError(f'Cannot compare {type(other)} to {type(self)}')
    return self.value < other.value
