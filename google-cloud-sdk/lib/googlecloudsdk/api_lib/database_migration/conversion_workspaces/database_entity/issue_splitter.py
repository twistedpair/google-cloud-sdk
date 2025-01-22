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
"""Database Migration Service conversion workspaces IssueSplitter."""
from typing import Sequence

from googlecloudsdk.generated_clients.apis.datamigration.v1 import datamigration_v1_messages as messages


class IssueSplitter:
  """Splits issues based on the entities they are related to."""

  def __init__(self, issues: Sequence[messages.EntityIssue]):
    """Initializes the IssueSplitter.

    Issues passed to the constructor relate to a single database entity and all
    of its sub-entities.

    Args:
      issues: The issues to split.
    """
    self._issue_id_to_issue_mapping = {issue.id: issue for issue in issues}

  def ExtractIssues(
      self,
      issue_ids: Sequence[str],
  ) -> Sequence[messages.EntityIssue]:
    """Extracts the issues based on the issue IDs and return them.

    Issues are removed from the splitter after they are extracted.

    Args:
      issue_ids: The issue IDs to extract.

    Returns:
      The issues that were extracted.
    """
    return [
        issue
        for issue_id in issue_ids
        if (issue := self._issue_id_to_issue_mapping.pop(issue_id, None))
        is not None
    ]

  def GetCurrentIssues(self) -> Sequence[messages.EntityIssue]:
    """The current issues stored in the splitter."""
    return list(self._issue_id_to_issue_mapping.values())
