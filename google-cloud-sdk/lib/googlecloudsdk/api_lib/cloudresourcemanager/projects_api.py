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

from apitools.base.py import exceptions
from apitools.base.py import list_pager

from googlecloudsdk.api_lib.cloudresourcemanager import projects_util
from googlecloudsdk.api_lib.resource_manager import folders
from googlecloudsdk.command_lib.iam import iam_util
from googlecloudsdk.command_lib.util import labels_util


def List(limit=None, filter=None):  # pylint: disable=redefined-builtin
  """Make API calls to List active projects.

  Args:
    limit: The number of projects to limit the resutls to. This limit is passed
           to the server and the server does the limiting.
    filter: The client side filter expression.

  Returns:
    Generator that yields projects
  """
  client = projects_util.GetClient()
  messages = projects_util.GetMessages()
  return list_pager.YieldFromList(
      client.projects,
      messages.CloudresourcemanagerProjectsListRequest(filter=filter),
      limit=limit,
      field='projects',
      predicate=
      projects_util.IsActive,
      batch_size_attribute='pageSize')


def Get(project_ref):
  """Get project information."""
  client = projects_util.GetClient()
  try:
    return client.projects.Get(
        client.MESSAGES_MODULE.CloudresourcemanagerProjectsGetRequest(
            projectId=project_ref.projectId))
  except exceptions.HttpError as error:
    raise projects_util.ConvertHttpError(error)


def Create(project_ref, display_name=None, parent=None, update_labels=None):
  """Create a new project.

  Args:
    project_ref: The identifier for the project
    display_name: Optional display name for the project
    parent: Optional for the project (ex. folders/123 or organizations/5231)
    update_labels: Optional labels to apply to the project

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
          labels=labels_util.UpdateLabels(
              None, messages.Project.LabelsValue, update_labels=update_labels)))


def Delete(project_ref):
  """Delete an existing project."""
  client = projects_util.GetClient()
  messages = projects_util.GetMessages()

  try:
    client.projects.Delete(
        messages.CloudresourcemanagerProjectsDeleteRequest(
            projectId=project_ref.Name()))
  except exceptions.HttpError as error:
    raise projects_util.ConvertHttpError(error)
  return projects_util.DeletedResource(project_ref.Name())


def Undelete(project_ref):
  """Undelete a project that has been deleted."""
  client = projects_util.GetClient()
  messages = projects_util.GetMessages()

  try:
    client.projects.Undelete(
        messages.CloudresourcemanagerProjectsUndeleteRequest(
            projectId=project_ref.Name()))
  except exceptions.HttpError as error:
    raise projects_util.ConvertHttpError(error)
  return projects_util.DeletedResource(project_ref.Name())


def Update(project_ref,
           name=None,
           parent=None,
           update_labels=None,
           remove_labels=None):
  """Update project information."""
  client = projects_util.GetClient()
  messages = projects_util.GetMessages()

  try:
    project = client.projects.Get(
        client.MESSAGES_MODULE.CloudresourcemanagerProjectsGetRequest(
            projectId=project_ref.projectId))
  except exceptions.HttpError as error:
    raise projects_util.ConvertHttpError(error)

  if name:
    project.name = name

  if parent:
    project.parent = parent

  project.labels = labels_util.UpdateLabels(project.labels,
                                            messages.Project.LabelsValue,
                                            update_labels=update_labels,
                                            remove_labels=remove_labels)
  try:
    return client.projects.Update(project)
  except exceptions.HttpError as error:
    raise projects_util.ConvertHttpError(error)


def GetIamPolicy(project_ref):
  """Get IAM policy for a given project."""
  client = projects_util.GetClient()
  messages = projects_util.GetMessages()

  policy_request = messages.CloudresourcemanagerProjectsGetIamPolicyRequest(
      resource=project_ref.Name(),
      getIamPolicyRequest=messages.GetIamPolicyRequest(),
  )
  try:
    return client.projects.GetIamPolicy(policy_request)
  except exceptions.HttpError as error:
    raise projects_util.ConvertHttpError(error)


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
  try:
    return client.projects.SetIamPolicy(policy_request)
  except exceptions.HttpError as error:
    raise projects_util.ConvertHttpError(error)


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

  try:
    return SetIamPolicy(project_ref, policy, update_mask)
  except exceptions.HttpError as error:
    raise projects_util.ConvertHttpError(error)


def AddIamPolicyBinding(project_ref, member, role):
  messages = projects_util.GetMessages()

  try:
    policy = GetIamPolicy(project_ref)
  except exceptions.HttpError as error:
    raise projects_util.ConvertHttpError(error)
  iam_util.AddBindingToIamPolicy(messages.Binding, policy, member, role)
  try:
    return SetIamPolicy(project_ref, policy)
  except exceptions.HttpError as error:
    raise projects_util.ConvertHttpError(error)


def RemoveIamPolicyBinding(project_ref, member, role):
  try:
    policy = GetIamPolicy(project_ref)
  except exceptions.HttpError as error:
    raise projects_util.ConvertHttpError(error)
  iam_util.RemoveBindingFromIamPolicy(policy, member, role)
  try:
    return SetIamPolicy(project_ref, policy)
  except exceptions.HttpError as error:
    raise projects_util.ConvertHttpError(error)


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
