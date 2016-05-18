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

"""Errors for projects."""
import json

from googlecloudsdk.core import exceptions


class ProjectNotFoundError(exceptions.Error):
  """The specified project does not exist."""

  def __init__(self, project_id):
    # TODO(user): Make the error message include how to create a project
    #                 once create has been implemented.
    message = ('Project [%s] does not exist.\nTo see available projects,'
               ' run:\n  $ gcloud projects list' % project_id)
    super(ProjectNotFoundError, self).__init__(message)


class ProjectAccessError(exceptions.Error):
  """User does not have permission to access the project."""

  def __init__(self, project_id):
    message = 'You do not have permission to access project [%s].' % project_id
    super(ProjectAccessError, self).__init__(message)


class ProjectMoveError(exceptions.Error):
  """The specified project already has a parent and can't be moved."""

  def __init__(self, project, organization_id):
    message = (
        'Cannot move project [%s] into organization [%s], it already has '
        'parent %s') % (project.projectId, organization_id, project.parent)
    super(ProjectMoveError, self).__init__(message)


class UnknownError(exceptions.Error):
  """An unknown error occurred."""

  def __init__(self, error):
    error_content = json.loads(error.content)['error']
    message = '%s %s' % (error_content['code'], error_content['message'])
    super(UnknownError, self).__init__(message)
