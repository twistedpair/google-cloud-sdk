# Copyright 2014 Google Inc. All Rights Reserved.

"""Errors for Projects."""
import json

from googlecloudsdk.core import exceptions


class ProjectNotFoundError(exceptions.Error):
  """The specified Project does not exist."""

  def __init__(self, project_id):
    # TODO(dbtucker): Make the error message include how to create a project
    #                 once create has been implemented.
    message = ('Project [%s] does not exist.\nTo see available projects,'
               ' run:\n  $ gcloud projects list' % project_id)
    super(ProjectNotFoundError, self).__init__(message)


class ProjectAccessError(exceptions.Error):
  """User does not have permission to access the Project."""

  def __init__(self, project_id):
    message = 'You do not have permission to access project [%s].' % project_id
    super(ProjectAccessError, self).__init__(message)


class UnknownError(exceptions.Error):
  """An unknown error occurred."""

  def __init__(self, error):
    error_content = json.loads(error.content)['error']
    message = '%s %s' % (error_content['code'], error_content['message'])
    super(UnknownError, self).__init__(message)
