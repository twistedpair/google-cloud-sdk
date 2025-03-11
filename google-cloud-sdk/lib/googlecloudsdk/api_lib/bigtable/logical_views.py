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


from googlecloudsdk.api_lib.bigtable import util


def Create(logical_view_ref, query):
  """Create a logical view.

  Args:
    logical_view_ref: A resource reference to the logical view to create.
    query: The query of the logical view.

  Returns:
    Created logical view resource object.
  """

  client = util.GetAdminClient()
  msgs = util.GetAdminMessages()

  instance_ref = logical_view_ref.Parent()

  msg = msgs.BigtableadminProjectsInstancesLogicalViewsCreateRequest(
      logicalView=msgs.LogicalView(query=query),
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
