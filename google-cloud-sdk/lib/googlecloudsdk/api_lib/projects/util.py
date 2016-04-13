# Copyright 2014 Google Inc. All Rights Reserved.
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

"""Util for projects."""

from datetime import datetime
import functools

from googlecloudsdk.api_lib.projects import errors
from googlecloudsdk.calliope import base
from googlecloudsdk.core import apis
from googlecloudsdk.core import resources
from googlecloudsdk.third_party.apitools.base.py import exceptions


class DeletedResource(object):
  """A deleted/undeleted resource returned by Run()."""

  def __init__(self, project_id):
    self.projectId = project_id  # pylint: disable=invalid-name, This is a resource attribute name.


class ProjectCommand(base.Command):
  """Common methods for a project command."""

  def Collection(self):
    return 'cloudresourcemanager.projects'

  def GetUriFunc(self):
    def _GetUri(resource):
      ref = resources.Parse(resource.projectId, collection=self.Collection())
      return ref.SelfLink()
    return _GetUri


def GetMessages():
  """Import and return the appropriate projects messages module."""
  return apis.GetMessagesModule('projects', 'v1beta1')


lifecycle = GetMessages().Project.LifecycleStateValueValuesEnum
lifecycle_description = {
    lifecycle.LIFECYCLE_STATE_UNSPECIFIED: 'unknown',
    lifecycle.ACTIVE: 'active',
    lifecycle.DELETE_REQUESTED: 'pending delete',
    lifecycle.DELETE_IN_PROGRESS: 'delete in progress',
}


def IsActive(project):
  """Returns true if the project's lifecycle state is 'active'.

  Args:
    project: A Project
  Returns:
    True if the Project's lifecycle state is 'active,' else False.
  """
  return project.lifecycleState == lifecycle.ACTIVE


def GetLifecycle(project):
  """Returns a reader friendly string description of a project's active state.

  Args:
    project: A Project with a LifecycleStateValueValues enum.

  Returns:
    String description of lifecycle state.
  """
  return lifecycle_description[project.lifecycleState]


def MsToDate(ms):
  """Takes a value of milliseconds since the epoch and returns readable date.

  Args:
    ms: Milliseconds since the epoch.

  Returns:
    Date in form YYYY-mm-dd HH:MM:SS

  Example:
    Input: 1371575781751
    Returns: 2013-06-18 13:16:21
  """
  return datetime.fromtimestamp(ms/1000.0).strftime('%Y-%m-%d %H:%M:%S')


def PrintAlignedColumns(writer, data):
  """Prints data in nicely aligned columns.

  Args:
    writer: A printer with a Print method.
    data: A list of lists/tuples.

  Example:
    Data of form:
        [('1', 'apple'), ('twoooo!', 'banana'), ('3', 'clementine')]
    will be printed as:
        1         apple
        twoooo!   banana
        3         clementine
  """
  width = max(len(word) for row in data for word in row)
  for row in data:
    writer.Print(''.join(word.ljust(width) for word in row))


def GetError(error):
  """Returns a more specific error from an HttpError.

  Args:
    error: HttpError resulting from unsuccessful call to API.

  Returns:
    Specific error based on error reason in HttpError.

  First line will parse project ID out of error url.
  Example:
   URL = .../v1beta1/projects/BAD_ID?prettyPrint=True&alt=json
   project_id = 'BAD_ID'
  """
  project_id = error.url.split('/')[-1].split('?')[0]
  if error.status_code == 403:
    return errors.ProjectAccessError(project_id)
  elif error.status_code == 404:
    return errors.ProjectNotFoundError(project_id)
  else:
    return errors.UnknownError(error)


def HandleHttpError(func):
  """Decorator that catches HttpError and raises corresponding error."""

  @functools.wraps(func)
  def CatchHTTPErrorRaiseHTTPException(*args, **kwargs):
    try:
      return func(*args, **kwargs)
    except exceptions.HttpError as error:
      raise GetError(error)

  return CatchHTTPErrorRaiseHTTPException


def GetClient():
  """Import and return the appropriate projects client.

  Returns:
    Cloud Resource Manager client for the appropriate release track.
  """
  return apis.GetClientInstance('projects', 'v1beta1')

