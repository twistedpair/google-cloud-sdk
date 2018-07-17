# -*- coding: utf-8 -*- #
# Copyright 2015 Google Inc. All Rights Reserved.
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
"""Useful commands for interacting with the Cloud Resource Management API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager

from googlecloudsdk.api_lib.cloudresourcemanager import projects_util
from googlecloudsdk.api_lib.resource_manager import folders
from googlecloudsdk.command_lib.iam import iam_util


def List(limit=None, filter=None, batch_size=500):  # pylint: disable=redefined-builtin
  """Make API calls to List active projects.

  Args:
    limit: The number of projects to limit the resutls to. This limit is passed
           to the server and the server does the limiting.
    filter: The client side filter expression.
    batch_size: the number of projects to get with each request.

  Returns:
    Generator that yields projects
  """
  client = projects_util.GetClient()
  messages = projects_util.GetMessages()
  return list_pager.YieldFromList(
      client.projects,
      messages.CloudresourcemanagerProjectsListRequest(
          filter=_AddActiveProjectFilter(filter)),
      batch_size=batch_size,
      limit=limit,
      field='projects',
      batch_size_attribute='pageSize')


def _AddActiveProjectFilter(filter_expr):
  if not filter_expr:
    return 'lifecycleState:ACTIVE'
  return 'lifecycleState:ACTIVE AND ({})'.format(filter_expr)


def Get(project_ref):
  """Get project information."""
  client = projects_util.GetClient()
  return client.projects.Get(
      client.MESSAGES_MODULE.CloudresourcemanagerProjectsGetRequest(
          projectId=project_ref.projectId))


def Create(project_ref, display_name=None, parent=None, labels=None):
  """Create a new project.

  Args:
    project_ref: The identifier for the project
    display_name: Optional display name for the project
    parent: Optional for the project (ex. folders/123 or organizations/5231)
    labels: Optional labels to apply to the project

  Returns:
    An Operation object which can be used to check on the progress of the
    project creation.
  """
  client = projects_util.GetClient()
  messages = projects_util.GetMessages()
  return client.projects.Create(
      messages.Project(
          projectId=project_ref.Name(),
          name=display_name if display_name else project_ref.Name(),
          parent=parent,
          labels=labels))


def Delete(project_ref):
  """Delete an existing project."""
  client = projects_util.GetClient()
  messages = projects_util.GetMessages()

  client.projects.Delete(
      messages.CloudresourcemanagerProjectsDeleteRequest(
          projectId=project_ref.Name()))
  return projects_util.DeletedResource(project_ref.Name())


def Undelete(project_ref):
  """Undelete a project that has been deleted."""
  client = projects_util.GetClient()
  messages = projects_util.GetMessages()

  client.projects.Undelete(
      messages.CloudresourcemanagerProjectsUndeleteRequest(
          projectId=project_ref.Name()))
  return projects_util.DeletedResource(project_ref.Name())


def Update(project_ref,
           name=None,
           parent=None,
           labels_diff=None):
  """Update project information."""
  client = projects_util.GetClient()
  messages = projects_util.GetMessages()

  project = client.projects.Get(
      client.MESSAGES_MODULE.CloudresourcemanagerProjectsGetRequest(
          projectId=project_ref.projectId))

  if name:
    project.name = name

  if parent:
    project.parent = parent

  if labels_diff:
    labels_update = labels_diff.Apply(messages.Project.LabelsValue,
                                      project.labels)
    if labels_update.needs_update:
      project.labels = labels_update.labels

  return client.projects.Update(project)


def GetIamPolicy(project_ref):
  """Get IAM policy for a given project."""
  client = projects_util.GetClient()
  messages = projects_util.GetMessages()

  policy_request = messages.CloudresourcemanagerProjectsGetIamPolicyRequest(
      resource=project_ref.Name(),
  )
  return client.projects.GetIamPolicy(policy_request)


def SetIamPolicy(project_ref, policy, update_mask=None):
  """Set IAM policy, for a given project."""
  client = projects_util.GetClient()
  messages = projects_util.GetMessages()

  set_iam_policy_request = messages.SetIamPolicyRequest(policy=policy)
  # Only include update_mask if provided, otherwise, leave the field unset.
  if update_mask is not None:
    set_iam_policy_request.updateMask = update_mask

  policy_request = messages.CloudresourcemanagerProjectsSetIamPolicyRequest(
      resource=project_ref.Name(),
      setIamPolicyRequest=set_iam_policy_request)
  return client.projects.SetIamPolicy(policy_request)


def SetIamPolicyFromFile(project_ref, policy_file):
  """Read projects IAM policy from a file, and set it."""
  messages = projects_util.GetMessages()
  policy = iam_util.ParsePolicyFile(policy_file, messages.Policy)
  update_mask = iam_util.ConstructUpdateMaskFromPolicy(policy_file)

  # To preserve the existing set-iam-policy behavior of always overwriting
  # bindings and etag, add bindings and etag to update_mask.
  if 'bindings' not in update_mask:
    update_mask += ',bindings'
  if 'etag' not in update_mask:
    update_mask += ',etag'

  return SetIamPolicy(project_ref, policy, update_mask)


def AddIamPolicyBinding(project_ref, member, role):
  messages = projects_util.GetMessages()

  policy = GetIamPolicy(project_ref)
  iam_util.AddBindingToIamPolicy(messages.Binding, policy, member, role)
  return SetIamPolicy(project_ref, policy)


def RemoveIamPolicyBinding(project_ref, member, role):
  policy = GetIamPolicy(project_ref)
  iam_util.RemoveBindingFromIamPolicy(policy, member, role)
  return SetIamPolicy(project_ref, policy)


def ParentNameToResourceId(parent_name):
  messages = projects_util.GetMessages()
  if not parent_name:
    return None
  elif parent_name.startswith('folders/'):
    return messages.ResourceId(
        id=folders.FolderNameToId(parent_name), type='folder')
  elif parent_name.startswith('organizations/'):
    return messages.ResourceId(
        id=parent_name[len('organizations/'):], type='organization')
