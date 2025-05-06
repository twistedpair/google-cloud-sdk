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
"""Bigtable logical-views API helper."""

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.bigtable import util


def Create(logical_view_ref, query, deletion_protection):
  """Create a logical view.

  Args:
    logical_view_ref: A resource reference to the logical view to create.
    query: The query of the logical view.
    deletion_protection: The deletion protection of the logical view.

  Returns:
    Created logical view resource object.
  """

  client = util.GetAdminClient()
  msgs = util.GetAdminMessages()

  instance_ref = logical_view_ref.Parent()

  logical_view = msgs.LogicalView(query=query)
  if deletion_protection is not None:
    logical_view.deletionProtection = deletion_protection

  msg = msgs.BigtableadminProjectsInstancesLogicalViewsCreateRequest(
      logicalView=logical_view,
      logicalViewId=logical_view_ref.Name(),
      parent=instance_ref.RelativeName(),
  )
  return client.projects_instances_logicalViews.Create(msg)


def Delete(logical_view_ref):
  """Delete a logical view.

  Args:
    logical_view_ref: A resource reference to the logical view to delete.

  Returns:
    Empty response.
  """
  client = util.GetAdminClient()
  msg = util.GetAdminMessages().BigtableadminProjectsInstancesLogicalViewsDeleteRequest(
      name=logical_view_ref.RelativeName()
  )
  return client.projects_instances_logicalViews.Delete(msg)


def Describe(logical_view_ref):
  """Describe a logical view.

  Args:
    logical_view_ref: A resource reference to the logical view to describe.

  Returns:
    Logical view resource object.
  """
  client = util.GetAdminClient()
  msg = util.GetAdminMessages().BigtableadminProjectsInstancesLogicalViewsGetRequest(
      name=logical_view_ref.RelativeName()
  )
  return client.projects_instances_logicalViews.Get(msg)


def List(instance_ref):
  """List logical views.

  Args:
    instance_ref: A resource reference of the instance to list logical views
      for.

  Returns:
    Generator of logical view resource objects.
  """
  client = util.GetAdminClient()
  msg = util.GetAdminMessages().BigtableadminProjectsInstancesLogicalViewsListRequest(
      parent=instance_ref.RelativeName()
  )
  return list_pager.YieldFromList(
      client.projects_instances_logicalViews,
      msg,
      field='logicalViews',
      batch_size_attribute=None,
  )


def Update(logical_view_ref, query, deletion_protection):
  """Update a logical view.

  Args:
    logical_view_ref: A resource reference to the logical view to update.
    query: The new query of the logical view.
    deletion_protection: The new deletion protection of the logical view.

  Returns:
    Long running operation.
  """

  client = util.GetAdminClient()
  msgs = util.GetAdminMessages()

  changed_fields = []
  logical_view = msgs.LogicalView()

  if query:
    changed_fields.append('query')
    logical_view.query = query

  if deletion_protection is not None:
    changed_fields.append('deletion_protection')
    logical_view.deletionProtection = deletion_protection

  msg = msgs.BigtableadminProjectsInstancesLogicalViewsPatchRequest(
      logicalView=logical_view,
      name=logical_view_ref.RelativeName(),
      updateMask=','.join(changed_fields),
  )

  return client.projects_instances_logicalViews.Patch(msg)
