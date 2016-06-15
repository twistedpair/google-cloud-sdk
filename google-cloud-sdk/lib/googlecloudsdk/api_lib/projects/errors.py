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
from googlecloudsdk.core import exceptions


class ProjectError(exceptions.Error):
  """Generic error for all project errors to inherit from."""
  pass


class ProjectAccessError(ProjectError):
  """User does not have permission to access the project."""

  def __init__(self, project_id):
    message = ('Project [{0}] does not exist, or you do not have permission to '
               'access it.').format(project_id)
    super(ProjectAccessError, self).__init__(message)


class ProjectMoveError(ProjectError):
  """The specified project already has a parent and can't be moved."""

  def __init__(self, project, organization_id):
    message = (
        'Cannot move project [%s] into organization [%s], it already has '
        'parent %s') % (project.projectId, organization_id, project.parent)
    super(ProjectMoveError, self).__init__(message)
