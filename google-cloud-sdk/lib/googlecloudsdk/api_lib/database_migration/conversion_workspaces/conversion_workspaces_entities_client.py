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
from typing import Any, Generator, Mapping, Optional

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.database_migration.conversion_workspaces import base_conversion_workspaces_client
from googlecloudsdk.api_lib.database_migration.conversion_workspaces.database_entity import entity_builder
from googlecloudsdk.api_lib.database_migration.conversion_workspaces.database_entity import entity_serializers


class ConversionWorkspacesEntitiesClient(
    base_conversion_workspaces_client.BaseConversionWorkspacesClient
):
  """Client for conversion workspaces Entities APIs."""

  def DescribeEntities(
      self,
      name: str,
      commit_id: str,
      uncommitted: bool,
      tree_type: str,
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
      tree_type: str,
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
    yield from list_pager.YieldFromList(
        service=self.cw_service,
        request=self._BuildDescribeEntitiesRequest(
            conversion_workspace_ref=name,
            commit_id=commit_id,
            uncommitted=uncommitted,
            tree_type=tree_type or 'DRAFT',
            filter_expr=filter_expr,
            include_ddls=True,
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
      include_ddls: bool = False,
  ):
    """Returns request to describe database entities in a conversion workspace.

    Args:
      conversion_workspace_ref: The conversion workspace reference.
      commit_id: The commit ID to describe issues for.
      uncommitted: Whether to describe issues for uncommitted changes.
      tree_type: The tree type to describe issues for.
      filter_expr: The filter expression to use.
      include_ddls: Whether to include DDLs in the response.

    Returns:
      The request to describe database entities in a conversion workspace.
    """

    view = (
        self.messages.DatamigrationProjectsLocationsConversionWorkspacesDescribeDatabaseEntitiesRequest.ViewValueValuesEnum.DATABASE_ENTITY_VIEW_FULL
        if include_ddls
        else self.messages.DatamigrationProjectsLocationsConversionWorkspacesDescribeDatabaseEntitiesRequest.ViewValueValuesEnum.DATABASE_ENTITY_VIEW_FULL_COMPACT
    )

    tree = self._GetTreeType(tree_type=tree_type)

    if (
        tree
        == self.messages.DatamigrationProjectsLocationsConversionWorkspacesDescribeDatabaseEntitiesRequest.TreeValueValuesEnum.SOURCE_TREE
    ):
      filter_expr = self.CombineFilters(
          filter_expr,
          self.parent_client.crud.GetGlobalFilter(
              name=conversion_workspace_ref,
          ),
      )

    return self.messages.DatamigrationProjectsLocationsConversionWorkspacesDescribeDatabaseEntitiesRequest(
        commitId=commit_id,
        conversionWorkspace=conversion_workspace_ref,
        uncommitted=uncommitted,
        tree=tree,
        view=view,
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
      builder = entity_builder.EntityBuilder(database_entity_proto=entity)
      entity_obj = builder.Build()
      yield from entity_serializers.GetSummaries(entity_obj=entity_obj)

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
      builder = entity_builder.EntityBuilder(database_entity_proto=entity)
      entity_obj = builder.Build()
      yield from entity_serializers.GetDdls(entity_obj=entity_obj)

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
      builder = entity_builder.EntityBuilder(database_entity_proto=entity)
      entity_obj = builder.Build()
      yield from entity_serializers.GetIssues(
          entity_obj=entity_obj,
          issue_severities=issue_severities,
      )
