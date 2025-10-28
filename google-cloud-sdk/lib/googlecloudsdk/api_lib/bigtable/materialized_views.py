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
"""Bigtable materialized-views API helper."""

from typing import Generator
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.bigtable import util
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.core import resources
from googlecloudsdk.generated_clients.apis.bigtableadmin.v2 import bigtableadmin_v2_messages


def Describe(
    materialized_view_ref: resources.Resource, view: str
) -> bigtableadmin_v2_messages.MaterializedView:
  """Describe a materialized view.

  Args:
    materialized_view_ref: A resource reference to the materialized view to
      describe.
    view: Specifies what type of information to return about the view. Valid
      values are 'schema', 'replication', and 'full'.

  Returns:
    materialized view resource object.
  """
  client = util.GetAdminClient()
  msgs = util.GetAdminMessages()

  get_materialized_view_request = (
      msgs.BigtableadminProjectsInstancesMaterializedViewsGetRequest
  )
  view_enum_type = get_materialized_view_request.ViewValueValuesEnum
  mapper = arg_utils.ChoiceEnumMapper(
      '--view',
      view_enum_type,
      custom_mappings={
          'SCHEMA_VIEW': 'schema',
          'REPLICATION_VIEW': 'replication',
          'FULL': 'full',
      },
  )
  view_enum = mapper.GetEnumForChoice(view)
  if view_enum is None:
    view_enum = view_enum_type.SCHEMA_VIEW

  msg = get_materialized_view_request(
      name=materialized_view_ref.RelativeName(), view=view_enum
  )
  return client.projects_instances_materializedViews.Get(msg)


def Create(
    materialized_view_ref: resources.Resource,
    query: str,
    deletion_protection: bool,
) -> bigtableadmin_v2_messages.MaterializedView:
  """Create a materialized view.

  Args:
    materialized_view_ref: A resource reference to the materialized view to
      create.
    query: The query of the materialized view.
    deletion_protection: Whether the materialized view is protected from
      deletion.

  Returns:
    Created materialized view resource object.
  """

  client = util.GetAdminClient()
  msgs = util.GetAdminMessages()

  instance_ref = materialized_view_ref.Parent()

  materialized_view = msgs.MaterializedView(query=query)
  if deletion_protection is not None:
    materialized_view.deletionProtection = deletion_protection

  msg = msgs.BigtableadminProjectsInstancesMaterializedViewsCreateRequest(
      materializedView=materialized_view,
      materializedViewId=materialized_view_ref.Name(),
      parent=instance_ref.RelativeName(),
  )
  return client.projects_instances_materializedViews.Create(msg)


def Delete(
    materialized_view_ref: resources.Resource,
) -> None:
  """Delete a materialized view.

  Args:
    materialized_view_ref: A resource reference to the materialized view to
      delete.
  """
  client = util.GetAdminClient()
  msg = util.GetAdminMessages().BigtableadminProjectsInstancesMaterializedViewsDeleteRequest(
      name=materialized_view_ref.RelativeName()
  )
  client.projects_instances_materializedViews.Delete(msg)


def List(
    instance_ref: resources.Resource,
    view: str,
) -> Generator[bigtableadmin_v2_messages.MaterializedView, None, None]:
  """List materialized views.

  Args:
    instance_ref: A resource reference of the instance to list materialized
      views for.
    view: Specifies what type of information to return about the views. The only
      supported value at this time is 'schema'.

  Returns:
    Generator of materialized view resource objects.
  """
  client = util.GetAdminClient()
  msgs = util.GetAdminMessages()

  list_materialized_view_request = (
      msgs.BigtableadminProjectsInstancesMaterializedViewsListRequest
  )
  view_enum_type = list_materialized_view_request.ViewValueValuesEnum
  mapper = arg_utils.ChoiceEnumMapper(
      '--view',
      view_enum_type,
      custom_mappings={
          'SCHEMA_VIEW': 'schema',
          'REPLICATION_VIEW': 'replication',
          'FULL': 'full',
      },
  )
  view_enum = mapper.GetEnumForChoice(view)
  # Only the schema view is supported for list materialized views at this time.
  if view_enum != view_enum_type.SCHEMA_VIEW:
    raise exceptions.BadArgumentException(
        view,
        "Only 'schema' view is supported for list materialized views.",
    )

  msg = list_materialized_view_request(
      parent=instance_ref.RelativeName(),
      view=view_enum,
  )
  return list_pager.YieldFromList(
      client.projects_instances_materializedViews,
      msg,
      field='materializedViews',
      batch_size_attribute=None,
  )


def Update(
    materialized_view_ref: resources.Resource, deletion_protection: bool
) -> bigtableadmin_v2_messages.MaterializedView:
  """Update a materialized view.

  Args:
    materialized_view_ref: A resource reference to the materialized view to
      update.
    deletion_protection: Whether the materialized view is protected from
      deletion.

  Returns:
    Updated materialized view resource object.
  """

  client = util.GetAdminClient()
  msgs = util.GetAdminMessages()

  msg = msgs.BigtableadminProjectsInstancesMaterializedViewsPatchRequest(
      materializedView=msgs.MaterializedView(
          deletionProtection=deletion_protection
      ),
      name=materialized_view_ref.RelativeName(),
      updateMask='deletion_protection',
  )

  return client.projects_instances_materializedViews.Patch(msg)
