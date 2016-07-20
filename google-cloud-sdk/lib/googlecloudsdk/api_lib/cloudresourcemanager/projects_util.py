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

import functools

from apitools.base.py import exceptions

from googlecloudsdk.api_lib.cloudresourcemanager import errors
from googlecloudsdk.core import apis


class DeletedResource(object):
  """A deleted/undeleted resource returned by Run()."""

  def __init__(self, project_id):
    self.projectId = project_id  # pylint: disable=invalid-name, This is a resource attribute name.


def GetMessages():
  """Import and return the appropriate projects messages module."""
  return apis.GetMessagesModule('projects', 'v1beta1')


def GetClient():
  """Import and return the appropriate projects client.

  Returns:
    Cloud Resource Manager client for the appropriate release track.
  """
  return apis.GetClientInstance('projects', 'v1beta1')


def IsActive(project):
  """Returns true if the project's lifecycle state is 'active'.

  Args:
    project: A Project
  Returns:
    True if the Project's lifecycle state is 'active,' else False.
  """
  lifecycle_enum = GetMessages().Project.LifecycleStateValueValuesEnum
  return project.lifecycleState == lifecycle_enum.ACTIVE


def GetError(error):
  """Returns a more specific Projects error from an HttpError.

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
  if error.status_code == 403 or error.status_code == 404:
    return errors.ProjectAccessError(project_id)
  return None


def HandleKnownHttpErrors(func):
  """Decorator that catches HttpError and raises corresponding error."""

  @functools.wraps(func)
  def CatchHTTPErrorRaiseProjectError(*args, **kwargs):
    try:
      return func(*args, **kwargs)
    except exceptions.HttpError as error:
      processed_error = GetError(error)
      if not processed_error:
        raise
      raise processed_error

  return CatchHTTPErrorRaiseProjectError
