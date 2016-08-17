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

from googlecloudsdk.api_lib.cloudresourcemanager import errors
from googlecloudsdk.api_lib.cloudresourcemanager import projects_util
from googlecloudsdk.api_lib.service_management import enable_api as services_enable_api
from googlecloudsdk.api_lib.service_management import services_util
from googlecloudsdk.command_lib.iam import iam_util
from googlecloudsdk.command_lib.util import labels_util
from googlecloudsdk.core import apis


def List(limit=None):
  """Make API calls to List active projects.

  Args:
    limit: The number of projects to limit the resutls to. This limit is passed
           to the server and the server does the limiting.

  Returns:
    Generator that yields projects
  """
  client = projects_util.GetClient()
  messages = projects_util.GetMessages()
  return list_pager.YieldFromList(
      client.projects,
      messages.CloudresourcemanagerProjectsListRequest(),
      limit=limit,
      field='projects',
      predicate=
      projects_util.IsActive,
      batch_size_attribute='pageSize')


def Get(project_ref):
  """Get project information."""
  client = projects_util.GetClient()
  try:
    return client.projects.Get(project_ref.Request())
  except exceptions.HttpError as error:
    raise projects_util.ConvertHttpError(error)


def Create(project_ref, project_name, enable_cloud_apis=True,
           update_labels=None):
  """Create a new project."""
  client = projects_util.GetClient()
  messages = projects_util.GetMessages()

  # Create project.
  project_creation_result = client.projects.Create(
      messages.CloudresourcemanagerProjectsCreateRequest(
          project=messages.Project(
              projectId=project_ref.Name(),
              name=project_name if project_name else project_ref.Name(),
              labels=labels_util.UpdateLabels(None,
                                              messages.Project.LabelsValue,
                                              update_labels=update_labels))))

  if enable_cloud_apis:
    # Enable cloudapis.googleapis.com
    services_client = apis.GetClientInstance('servicemanagement', 'v1')
    enable_operation = services_enable_api.EnableServiceApiCall(
        project_ref.Name(), 'cloudapis.googleapis.com')
    services_util.WaitForOperation(enable_operation.name, services_client)
    # TODO(user): Retry in case it failed?

  return project_creation_result


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


def Update(project_ref, name=None, organization=None, update_labels=None,
           remove_labels=None):
  """Update project information."""
  client = projects_util.GetClient()
  messages = projects_util.GetMessages()

  try:
    project = client.projects.Get(project_ref.Request())
  except exceptions.HttpError as error:
    raise projects_util.ConvertHttpError(error)

  if name:
    project.name = name
  if organization:
    if project.parent is not None:
      raise errors.ProjectMoveError(project, organization)
    project.parent = messages.ResourceId(id=organization, type='organization')
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


def SetIamPolicy(project_ref, policy):
  """Set IAM policy, for a given project."""
  client = projects_util.GetClient()
  messages = projects_util.GetMessages()
  policy_request = messages.CloudresourcemanagerProjectsSetIamPolicyRequest(
      resource=project_ref.Name(),
      setIamPolicyRequest=messages.SetIamPolicyRequest(policy=policy))
  try:
    return client.projects.SetIamPolicy(policy_request)
  except exceptions.HttpError as error:
    raise projects_util.ConvertHttpError(error)


def SetIamPolicyFromFile(project_ref, policy_file):
  """Read projects IAM policy from a file, and set it."""
  messages = projects_util.GetMessages()

  policy = iam_util.ParseJsonPolicyFile(policy_file, messages.Policy)
  try:
    return SetIamPolicy(project_ref, policy)
  except exceptions.HttpError as error:
    raise projects_util.ConvertHttpError(error)


def AddIamPolicyBinding(project_ref, member, role):
  messages = projects_util.GetMessages()

  try:
    policy = GetIamPolicy(project_ref)
  except exceptions.HttpError as error:
    raise projects_util.ConvertHttpError(error)
  iam_util.AddBindingToIamPolicy(messages, policy, member, role)
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
