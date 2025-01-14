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
"""Database Migration Service conversion workspaces Entities APIs."""

import functools
from typing import Any, Generator, Iterable, Mapping, Optional

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.database_migration.conversion_workspaces import base_conversion_workspaces_client


class ConversionWorkspacesEntitiesClient(
    base_conversion_workspaces_client.BaseConversionWorkspacesClient
):
  """Client for conversion workspaces Entities APIs."""

  def DescribeEntities(
      self,
      name: str,
      commit_id: str,
      uncommitted: bool,
      tree_type: Optional[str],
      filter_expr: str,
      page_size: int,
  ):
    """Describes database entities in a conversion worksapce.

    Args:
      name: str, the name for conversion worksapce being described.
      commit_id: str, the commit ID to describe issues for.
      uncommitted: bool, whether to describe issues for uncommitted changes.
      tree_type: str, the tree type to describe issues for.
      filter_expr: str, the filter expression to use.
      page_size: int, the page size to use.

    Yields:
      Described entities for the conversion worksapce.
    """
    filter_expr = self._CombineFilters(
        filter_expr,
        self._GetGlobalFilter(name=name),
    )

    yield from list_pager.YieldFromList(
        service=self.cw_service,
        request=self._BuildDescribeEntitiesRequest(
            conversion_workspace_ref=name,
            commit_id=commit_id,
            uncommitted=uncommitted,
            tree_type=tree_type,
            filter_expr=filter_expr,
        ),
        method='DescribeDatabaseEntities',
        batch_size_attribute='pageSize',
        field='databaseEntities',
        get_field_func=self._ExtractEntitiesFromDescribeEntitiesResponse,
        batch_size=page_size,
    )

  def DescribeDDLs(
      self,
      name: str,
      commit_id: str,
      uncommitted: bool,
      tree_type: Optional[str],
      filter_expr: str,
      page_size: int,
  ):
    """Describe DDLs in a conversion worksapce.

    Args:
      name: str, the name for conversion worksapce being described.
      commit_id: str, the commit ID to describe issues for.
      uncommitted: bool, whether to describe issues for uncommitted changes.
      tree_type: str, the tree type to describe issues for.
      filter_expr: str, the filter expression to use.
      page_size: int, the page size to use.

    Yields:
      DDLs for the entities of the conversion worksapce.
    """
    filter_expr = self._CombineFilters(
        filter_expr,
        self._GetGlobalFilter(name=name),
    )

    yield from list_pager.YieldFromList(
        service=self.cw_service,
        request=self._BuildDescribeEntitiesRequest(
            conversion_workspace_ref=name,
            commit_id=commit_id,
            uncommitted=uncommitted,
            tree_type=tree_type or 'DRAFT',
            filter_expr=filter_expr,
        ),
        method='DescribeDatabaseEntities',
        batch_size_attribute='pageSize',
        field='databaseEntities',
        get_field_func=self._ExtractDdlsFromDescribeEntitiesResponse,
        batch_size=page_size,
    )

  def DescribeIssues(
      self,
      name: str,
      commit_id: str,
      uncommitted: bool,
      filter_expr: str,
      page_size: int,
  ):
    """Describe database entity issues in a conversion worksapce.

    Args:
      name: str, the name for conversion worksapce being described.
      commit_id: str, the commit ID to describe issues for.
      uncommitted: bool, whether to describe issues for uncommitted changes.
      filter_expr: str, the filter expression to use.
      page_size: int, the page size to use.

    Yields:
      Issues found for the database entities of the conversion worksapce.
    """
    filter_expr = self._CombineFilters(
        filter_expr,
        self._GetGlobalFilter(name=name),
    )

    for tree_type in ('SOURCE', 'DRAFT'):
      yield from list_pager.YieldFromList(
          service=self.cw_service,
          request=self._BuildDescribeEntitiesRequest(
              conversion_workspace_ref=name,
              commit_id=commit_id,
              uncommitted=uncommitted,
              tree_type=tree_type,
              filter_expr=filter_expr,
          ),
          method='DescribeDatabaseEntities',
          batch_size_attribute='pageSize',
          field='databaseEntities',
          get_field_func=functools.partial(
              self._ExtractIssuesFromDescribeEntitiesResponse,
              issue_severities=frozenset([
                  self.messages.EntityIssue.SeverityValueValuesEnum.ISSUE_SEVERITY_WARNING,
                  self.messages.EntityIssue.SeverityValueValuesEnum.ISSUE_SEVERITY_ERROR,
              ]),
          ),
          batch_size=page_size,
      )

  def _BuildDescribeEntitiesRequest(
      self,
      conversion_workspace_ref: str,
      commit_id: str,
      uncommitted: bool,
      tree_type: str,
      filter_expr: str,
  ):
    """Returns request to describe database entities in a conversion workspace.

    Args:
      conversion_workspace_ref: The conversion workspace reference.
      commit_id: The commit ID to describe issues for.
      uncommitted: Whether to describe issues for uncommitted changes.
      tree_type: The tree type to describe issues for.
      filter_expr: The filter expression to use.

    Returns:
      The request to describe database entities in a conversion workspace.
    """
    return self.messages.DatamigrationProjectsLocationsConversionWorkspacesDescribeDatabaseEntitiesRequest(
        commitId=commit_id,
        conversionWorkspace=conversion_workspace_ref,
        uncommitted=uncommitted,
        tree=self._GetTreeType(tree_type=tree_type),
        view=self.messages.DatamigrationProjectsLocationsConversionWorkspacesDescribeDatabaseEntitiesRequest.ViewValueValuesEnum.DATABASE_ENTITY_VIEW_FULL,
        filter=filter_expr,
    )

  def _GetTreeType(
      self,
      tree_type: Optional[str],
      default_tree_type: Optional[str] = None,
  ):
    """Returns the tree type for database entities.

    Args:
      tree_type: The tree type to get.
      default_tree_type: The default tree type to use if tree_type is None.

    Returns:
      The tree type for database entities.
    """
    tree_type_str_to_enum = {
        'SOURCE': (
            self.messages.DatamigrationProjectsLocationsConversionWorkspacesDescribeDatabaseEntitiesRequest.TreeValueValuesEnum.SOURCE_TREE
        ),
        'DRAFT': (
            self.messages.DatamigrationProjectsLocationsConversionWorkspacesDescribeDatabaseEntitiesRequest.TreeValueValuesEnum.DRAFT_TREE
        ),
    }
    return tree_type_str_to_enum.get(
        tree_type or default_tree_type,
        self.messages.DatamigrationProjectsLocationsConversionWorkspacesDescribeDatabaseEntitiesRequest.TreeValueValuesEnum.DB_TREE_TYPE_UNSPECIFIED,
    )

  def _ExtractEntitiesFromDescribeEntitiesResponse(
      self,
      response,
      entities_field: str,
  ) -> Generator[Mapping[str, Any], None, None]:
    """Extract entities from describe entities response.

    Args:
      response: The GetDatabaseEntities response to extract entities from.
      entities_field: The field in the response containing the entities.

    Yields:
      Entities for the conversion worksapce.
    """
    for entity in getattr(response, entities_field):
      yield {
          'parentEntity': entity.parentEntity,
          'shortName': entity.shortName,
          'tree': entity.tree,
          'entityType': self._RemovePrefix(
              value=str(entity.entityType),
              prefix='DATABASE_ENTITY_TYPE_',
          ),
          'status': self._GetEntityStatus(entity=entity),
      }

  def _ExtractDdlsFromDescribeEntitiesResponse(
      self,
      response,
      entities_field: str,
  ) -> Generator[str, None, None]:
    """Extract DDLs from describe entities response.

    Args:
      response: The GetDatabaseEntities response to extract DDLs from.
      entities_field: The field in the response containing the entities.

    Yields:
      DDLs for the entities of the conversion worksapce.
    """
    for entity in getattr(response, entities_field):
      for ddl in entity.entityDdl:
        yield ddl

  def _ExtractIssuesFromDescribeEntitiesResponse(
      self,
      response,
      entities_field: str,
      issue_severities,
  ) -> Generator[Mapping[str, Any], None, None]:
    """Extract issues from describe entities response.

    Args:
      response: The GetDatabaseEntities response to extract issues from.
      entities_field: The field in the response containing the entities.
      issue_severities: The issue severities to extract.

    Yields:
      Issues with high severity found for the database entities of the
      conversion worksapce.
    """

    for entity in getattr(response, entities_field):
      for issue in entity.issues:
        if issue.severity not in issue_severities:
          continue

        yield {
            'parentEntity': entity.parentEntity,
            'shortName': entity.shortName,
            'entityType': self._RemovePrefix(
                value=str(entity.entityType),
                prefix='DATABASE_ENTITY_TYPE_',
            ),
            'issueType': str(issue.type).replace('ISSUE_TYPE_', ''),
            'issueSeverity': self._RemovePrefix(
                value=str(issue.severity),
                prefix='ISSUE_SEVERITY_',
            ),
            'issueCode': issue.code,
            'issueMessage': issue.message,
        }

  def _GetEntityStatus(self, entity) -> str:
    """Get entity status.

    The status is determined by the highest severity issue found for the entity.

    Args:
      entity: Entity to get status for.

    Returns:
      Entity status: `ACTION_REQUIRED'/`REVIEW_RECOMMENDED`/`NO_ISSUES`.
    """
    severities = set(map(lambda issue: issue.severity, entity.issues))
    if (
        self.messages.EntityIssue.SeverityValueValuesEnum.ISSUE_SEVERITY_ERROR
        in severities
    ):
      return 'ACTION_REQUIRED'
    if (
        self.messages.EntityIssue.SeverityValueValuesEnum.ISSUE_SEVERITY_WARNING
        in severities
    ):
      return 'REVIEW_RECOMMENDED'
    return 'NO_ISSUES'

  def _GetAdditionalProperties(self, name: str) -> Mapping[str, Any]:
    """Get conversion workspace additional properties.

    Args:
      name: The name of the conversion workspace.

    Returns:
      The conversion workspace additional properties.
    """
    conversion_workspace = self.parent_client.crud.Read(name=name)
    if not conversion_workspace.globalSettings:
      return {}

    return {
        additional_property.key: additional_property.value
        for additional_property in conversion_workspace.globalSettings.additionalProperties
    }

  def _GetGlobalFilter(self, name: str) -> str:
    """Get global filter for a conversion workspace.

    If no global filter is set, '*' will be returned.

    Args:
      name: The name of the conversion workspace.

    Returns:
      The global filter for the conversion workspace.
    """
    return self._GetAdditionalProperties(name).get('filter', '*')

  def _CombineFilters(
      self,
      *filter_exprs: Iterable[Optional[str]],
  ) -> Optional[str]:
    """Combine filter expression with global filter.

    Args:
      *filter_exprs: Filter expressions to combine.

    Returns:
      Combined filter expression (or None if no filter expressions are
      provided).
    """

    filter_exprs = tuple(
        filter(
            lambda filter_expr: filter_expr and filter_expr != '*',
            filter_exprs,
        )
    )

    if not filter_exprs:
      return None
    if len(filter_exprs) == 1:
      return filter_exprs[0]

    return ' AND '.join(
        map(lambda filter_expr: f'({filter_expr})', filter_exprs)
    )

  def _RemovePrefix(self, value: str, prefix: str) -> str:
    """Remove a prefix from a string, if it exists.

    Args:
      value: The value to remove the prefix from.
      prefix: The prefix to remove.

    Returns:
        The value with the prefix removed.
    """
    return value[len(prefix) :] if value.startswith(prefix) else value
