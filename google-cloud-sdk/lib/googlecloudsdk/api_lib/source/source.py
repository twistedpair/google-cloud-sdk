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

"""Source apis layer."""
import json
import os
import sys

from apitools.base.py import exceptions

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import exceptions as base_exceptions
from googlecloudsdk.core import exceptions as core_exceptions


class RepoCreationError(core_exceptions.Error):
  """Unable to create repo."""

  def __init__(self, message):
    super(RepoCreationError, self).__init__(message)


class RepoDeletionError(exceptions.Error):
  """Unable to delete repo."""

  def __init__(self, message):
    super(RepoDeletionError, self).__init__(message)


class RepoNoExistError(exceptions.Error):
  """Repo does not exist."""

  def __init__(self, message):
    super(RepoNoExistError, self).__init__(message)


# TODO(b/36057455): Avoid initializing this at import time.
messages = apis.GetMessagesModule('source', 'v1')


def _NormalizeToSourceAPIPath(path):
  """Fix an OS-native path to conform to the Unix/Source API style.

  Args:
    path: (string) An OS-native path (e.g. "/foo/bar" on Unix or "foo\bar" on
      Windows.
  Returns:
    (string) The path converted to Unix/Source API style. '\' characters will
    be converted to '/' on Windows.
    TODO(b/36052477) Consider whether it makes sense to strip drive letters.
  """

  return path.replace(os.sep, '/')


class NoEndpointException(Exception):

  def __str__(self):
    return (
        'Source endpoint not initialized. Source.SetApiEndpoint must be '
        'called before using this module.')


class FileTooBigException(Exception):

  def __init__(self, name, size, max_size):
    super(FileTooBigException, self).__init__()
    self.name = name
    self.size = size
    self.max_size = max_size

  def __str__(self):
    return (
        'Could not write file "{0}" because it was too large '
        '({1} bytes). Max size is {2} bytes').format(
            self.name, self.size, self.max_size)


def _GetViolationsFromError(error_info):
  """Looks for violations descriptions in error message.

  Args:
    error_info: json containing error information.
  Returns:
    List of violations descriptions.
  """
  result = ''
  details = None
  try:
    if 'details' in error_info:
      details = error_info['details']
    for field in details:
      if 'fieldViolations' in field:
        violations = field['fieldViolations']
        for violation in violations:
          if 'description' in violation:
            result += violation['description'] + '\n'
  except (ValueError, TypeError):
    pass
  return result


# TODO(b/26202997): make this more general to be used by other library code.
def GetHttpErrorMessage(error):
  """Returns a human readable string representation from the http response.

  Args:
    error: HttpException representing the error response.

  Returns:
    A human readable string representation of the error.
  """
  status = error.response.status
  code = error.response.reason
  message = ''
  try:
    data = json.loads(error.content)
  except ValueError:
    data = error.content

  if 'error' in data:
    try:
      error_info = data['error']
      if 'message' in error_info:
        message = error_info['message']
    except (ValueError, TypeError):
      message = data
    violations = _GetViolationsFromError(error_info)
    if violations:
      message += '\nProblems:\n' + violations
  else:
    message = data
  return 'ResponseError: status=[{0}], code=[{1}], message=[{2}]'.format(
      status, code, message)


class Source(object):
  """Base class for source api wrappers."""
  _client = None
  _resource_parser = None

  def _CheckClient(self):
    if not self._client:
      raise NoEndpointException()

  @classmethod
  def SetApiEndpoint(cls):
    cls._client = apis.GetClientInstance('source', 'v1')

  @classmethod
  def SetResourceParser(cls, parser):
    cls._resource_parser = parser


class Project(Source):
  """Abstracts source project."""

  def __init__(self, project_id):
    self._CheckClient()
    self._id = project_id

  def ListRepos(self):
    """Returns list of repos."""
    request = messages.SourceProjectsReposListRequest(projectId=self._id)
    try:
      return self._client.projects_repos.List(request).repos
    except exceptions.HttpError as error:
      msg = GetHttpErrorMessage(error)
      unused_type, unused_value, traceback = sys.exc_info()
      raise base_exceptions.HttpException, msg, traceback

  def GetRepo(self, repo_name):
    """Finds details on the named repo, if it exists.

    Args:
      repo_name: (string) The name of the repo to create.
    Returns:
      (messages.Repo) The full definition of the new repo, as reported by
        the server.
      Returns None if the repo does not exist.
    """
    if not repo_name:
      repo_name = 'default'
    request = messages.SourceProjectsReposGetRequest(
        projectId=self._id, repoName=repo_name)
    try:
      return self._client.projects_repos.Get(request)
    except exceptions.HttpError as e:
      # If the repo does not exist, we get an HTTP 404
      if e.status_code != 404:
        raise e
      return None

  def CreateRepo(self, repo_name, vcs=messages.Repo.VcsValueValuesEnum.GIT):
    """Creates a repo.

    Args:
      repo_name: (string) The name of the repo to create.
      vcs: (messages.Repo.VcsValueValuesEnum) The repo type.
    Returns:
      (messages.Repo) The full definition of the new repo, as reported by
        the server.
    """
    request = messages.Repo(
        projectId=self._id,
        name=repo_name,
        vcs=vcs)
    return self._client.projects_repos.Create(request)

  def DeleteRepo(self, repo_name):
    """Deletes a repo.

    Args:
      repo_name: (string) The name of the repo to delete.
    """
    request = messages.SourceProjectsReposDeleteRequest(
        projectId=self._id,
        repoName=repo_name)
    self._client.projects_repos.Delete(request)


class Repo(Source):
  """Abstracts a source repository.

  TODO(b/36055862) Increase coverage of the API.
  """

  def __init__(self, project_id, name=''):
    """Initialize to wrap the given repo in a project.

    Args:
      project_id: (string) The id of the project.
      name: (string) The name of the repo. If not specified, use the default
        repo for the project.
    """
    self._CheckClient()
    if not name:
      name = 'default'
    self._repo_name = name
    self._project_id = project_id

  def ListWorkspaces(self):
    """Request a list of workspaces.

    Yields:
      (Workspace) The list of workspaces.
    """
    request = messages.SourceProjectsReposWorkspacesListRequest(
        projectId=self._project_id, repoName=self._repo_name,
        view=messages.SourceProjectsReposWorkspacesListRequest.
        ViewValueValuesEnum.MINIMAL)
    response = self._client.projects_repos_workspaces.List(request)
    for ws in response.workspaces:
      yield Workspace(self._project_id, ws.id.name, repo_name=self._repo_name,
                      state=ws)

  def GetWorkspace(self, workspace_name):
    """Finds details on the named workspace, if it exists.

    Args:
      workspace_name: (string) The name of the workspace to create.
    Returns:
      (messages.Workspace) The full definition of the new workspace, as
        reported by the server.
      Returns None if the workspace does not exist.
    """
    if not workspace_name:
      workspace_name = 'default'
    request = messages.SourceProjectsReposWorkspacesGetRequest(
        projectId=self._project_id, repoName=self._repo_name,
        name=workspace_name)
    ws = self._client.projects_repos_workspaces.Get(request)
    return Workspace(self._project_id, ws.id.name, repo_name=self._repo_name,
                     state=ws)

  def CreateWorkspace(self, workspace_name, alias_name, expected_baseline=None):
    """Create a new workspace in the repo.

    Args:
      workspace_name: (string) The name of the new workspace. Must be unique.
      alias_name: (string) The alias to use as a baseline for the workspace.
        If the alias does not exist, the workspace will have no baseline, and
        when it is commited, this name will be used to create a new movable
        alias referring to the new root revision created by this workspace.
      expected_baseline: (string) The expected current revision ID for the
        alias specified by alias_name. If specified, this value must match the
        alias's current revision ID at the time CreateWorkspace is called.
    Returns:
      (Workspace) The workspace that was created.
    """
    request = messages.SourceProjectsReposWorkspacesCreateRequest(
        projectId=self._project_id, repoName=self._repo_name,
        createWorkspaceRequest=messages.CreateWorkspaceRequest(
            workspace=messages.Workspace(
                id=messages.CloudWorkspaceId(name=workspace_name),
                alias=alias_name,
                baseline=expected_baseline)))
    return Workspace(
        self._project_id, workspace_name, repo_name=self._repo_name,
        state=self._client.projects_repos_workspaces.Create(request))

  def DeleteWorkspace(self, workspace_name, current_snapshot=None):
    """Delete a workspace from the repo.

    Args:
      workspace_name: (string) The name of the new workspace. Must be unique.
      current_snapshot: (string) The current snapshot ID of the workspace,
        used to verify that the workspace hasn't changed. If not None, the
        delete will succeed if and only if the snapshot ID of the workspace
        matches this value.
    """
    request = messages.SourceProjectsReposWorkspacesDeleteRequest(
        projectId=self._project_id, repoName=self._repo_name,
        name=workspace_name, currentSnapshotId=current_snapshot)
    self._client.projects_repos_workspaces.Delete(request)


class Workspace(Source):
  """Abstracts a workspace."""

  # Maximum amount of data to buffer/maximum file size. Each modification
  # to the workspace is a single POST request, and anything more than a few
  # hundred KB tends to trigger DEADLINE_EXCEEDED errors. Empirically, 256KB
  # is a good threshold.
  SIZE_THRESHOLD = 256 * 2**10

  def __init__(self, project_id, workspace_name, repo_name='', state=None):
    """Initialize from a workspace message.

    Args:
      project_id: (string) The project ID for the workspace.
      workspace_name: (string) The name of the workspace
      repo_name: (string) The repo containing the workspace. If not specified,
        use the default repo for the project.
      state: (messages.Workspace) Server-supplied workspace information.
        Since this argument usually comes from a call to the server, the repo
        will usually be specified by a uid rather than a name.
    """
    self._CheckClient()
    self._project_id = project_id
    self._repo_name = repo_name
    self._workspace_name = workspace_name
    self._pending_actions = []
    self._workspace_state = state
    self._post_callback = None

  def __eq__(self, other):
    return isinstance(other, self.__class__) and str(self) == str(other)

  def __ne__(self, other):
    return not self.__eq__(other)

  def __repr__(self):
    return '<Workspace {0}, Project={1}, Repo={2}>'.format(
        self._workspace_name, self._project_id, self._repo_name)

  @property
  def name(self):
    return self._workspace_name

  def SetPostCallback(self, callback):
    """Sets a notification function to be called when actions are posted.

    Args:
      callback: (lambda(int)) A function to call with the number of actions
        posted to the server after the workspace has been modified.
    """

    self._post_callback = callback

  def FlushPendingActions(self, check_size_threshold=False):
    """Flushes all pending actions.

    Args:
      check_size_threshold: (boolean) If true, check if the total size of the
        contents of all pending actions exceeds SIZE_THRESHOLD
    """

    if not self._pending_actions:
      return
    if check_size_threshold:
      total = 0
      for a in self._pending_actions:
        if a.writeAction:
          total += len(a.writeAction.contents) + len(a.writeAction.path)
      if total < self.SIZE_THRESHOLD:
        return
    request = messages.SourceProjectsReposWorkspacesModifyWorkspaceRequest(
        projectId=self._project_id, repoName=self._repo_name,
        name=self._workspace_name,
        modifyWorkspaceRequest=messages.ModifyWorkspaceRequest(
            actions=self._pending_actions))
    self._workspace_state = (
        self._client.projects_repos_workspaces.ModifyWorkspace(request))
    if self._post_callback:
      self._post_callback(len(self._pending_actions))
    self._pending_actions = []

  def WriteFile(self, path, contents,
                mode=messages.WriteAction.ModeValueValuesEnum.NORMAL):
    """Schedule an action to create or modify a file.

    Args:
      path: The path of the file to write.
      contents: The new contents of the file.
      mode: The new mode of the file.
    Raises:
      FileTooBigException: Indicates that the file contents are bigger than the
        maximum size supported by ModifyWorkspace.
    """

    if len(contents) > self.SIZE_THRESHOLD:
      raise FileTooBigException(path, len(contents), self.SIZE_THRESHOLD)

    path = _NormalizeToSourceAPIPath(path)
    self._pending_actions.append(messages.Action(
        writeAction=messages.WriteAction(
            path=path, contents=contents, mode=mode)))
    self.FlushPendingActions(check_size_threshold=True)
