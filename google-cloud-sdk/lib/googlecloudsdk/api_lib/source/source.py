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

from apitools.base.py import exceptions

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import exceptions as base_exceptions
from googlecloudsdk.core import exceptions as core_exceptions


class RepoCreationError(core_exceptions.Error):
  """Unable to create repo."""


class RepoDeletionError(exceptions.Error):
  """Unable to delete repo."""


class RepoNoExistError(exceptions.Error):
  """Repo does not exist."""


def _NormalizeToSourceAPIPath(path):
  r"""Fix an OS-native path to conform to the Unix/Source API style.

  Args:
    path: (string) An OS-native path (e.g. "/foo/bar" on Unix or "foo\bar" on
      Windows.
  Returns:
    (string) The path converted to Unix/Source API style. '\' characters will
    be converted to '/' on Windows.
    TODO(b/36052477) Consider whether it makes sense to strip drive letters.
  """

  return path.replace(os.sep, '/')


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


def GetClientInstance():
  return apis.GetClientInstance('source', 'v1')


def GetMessagesModule(client=None):
  client = client or GetClientInstance()
  return client.MESSAGES_MODULE


class Project(object):
  """Abstracts source project."""

  def __init__(self, project_id, client=None, messages=None):
    self._id = project_id
    self.client = client or GetClientInstance()
    self.messages = messages or GetMessagesModule(client)
    self._service = self.client.projects_repos

  def ListRepos(self):
    """Returns list of repos."""
    request = self.messages.SourceProjectsReposListRequest(projectId=self._id)
    try:
      return self._service.List(request).repos
    except exceptions.HttpError as error:
      core_exceptions.reraise(
          base_exceptions.HttpException(GetHttpErrorMessage(error)))

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
    request = self.messages.SourceProjectsReposGetRequest(
        projectId=self._id, repoName=repo_name)
    try:
      return self._service.Get(request)
    except exceptions.HttpNotFoundError:
      # If the repo does not exist, we get an HTTP 404
      return None

  def CreateRepo(self, repo_name, vcs=None):
    """Creates a repo.

    Args:
      repo_name: (string) The name of the repo to create.
      vcs: (messages.Repo.VcsValueValuesEnum) The repo type.
    Returns:
      (messages.Repo) The full definition of the new repo, as reported by
        the server.
    """
    vcs = vcs or self.messages.Repo.VcsValueValuesEnum.GIT
    request = self.messages.Repo(
        projectId=self._id,
        name=repo_name,
        vcs=vcs)
    return self._service.Create(request)

  def DeleteRepo(self, repo_name):
    """Deletes a repo.

    Args:
      repo_name: (string) The name of the repo to delete.
    """
    request = self.messages.SourceProjectsReposDeleteRequest(
        projectId=self._id,
        repoName=repo_name)
    self._service.Delete(request)


class Repo(object):
  """Abstracts a source repository.

  TODO(b/36055862) Increase coverage of the API.
  """

  def __init__(self, project_id, name='', client=None, messages=None):
    """Initialize to wrap the given repo in a project.

    Args:
      project_id: (string) The id of the project.
      name: (string) The name of the repo. If not specified, use the default
        repo for the project.
      client: (apitools.BaseApiService) The API client to use.
      messages: (module) The module containing the API messages to use.
    """
    if not name:
      name = 'default'
    self._repo_name = name
    self._project_id = project_id
    self.client = client or GetClientInstance()
    self.messages = messages or GetMessagesModule(client)
    self._service = self.client.projects_repos_workspaces

  def ListWorkspaces(self):
    """Request a list of workspaces.

    Yields:
      (Workspace) The list of workspaces.
    """
    request = self.messages.SourceProjectsReposWorkspacesListRequest(
        projectId=self._project_id, repoName=self._repo_name,
        view=self.messages.SourceProjectsReposWorkspacesListRequest.
        ViewValueValuesEnum.MINIMAL)
    response = self._service.List(request)
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
    request = self.messages.SourceProjectsReposWorkspacesGetRequest(
        projectId=self._project_id, repoName=self._repo_name,
        name=workspace_name)
    ws = self._service.Get(request)
    return Workspace(self._project_id, ws.id.name, repo_name=self._repo_name,
                     state=ws)

  def CreateWorkspace(self, workspace_name, alias_name, expected_baseline=None):
    """Create a new workspace in the repo.

    Args:
      workspace_name: (string) The name of the new workspace. Must be unique.
      alias_name: (string) The alias to use as a baseline for the workspace.
        If the alias does not exist, the workspace will have no baseline, and
        when it is committed, this name will be used to create a new movable
        alias referring to the new root revision created by this workspace.
      expected_baseline: (string) The expected current revision ID for the
        alias specified by alias_name. If specified, this value must match the
        alias's current revision ID at the time CreateWorkspace is called.
    Returns:
      (Workspace) The workspace that was created.
    """
    request = self.messages.SourceProjectsReposWorkspacesCreateRequest(
        projectId=self._project_id, repoName=self._repo_name,
        createWorkspaceRequest=self.messages.CreateWorkspaceRequest(
            workspace=self.messages.Workspace(
                id=self.messages.CloudWorkspaceId(name=workspace_name),
                alias=alias_name,
                baseline=expected_baseline)))
    return Workspace(
        self._project_id, workspace_name, repo_name=self._repo_name,
        state=self._service.Create(request))

  def DeleteWorkspace(self, workspace_name, current_snapshot=None):
    """Delete a workspace from the repo.

    Args:
      workspace_name: (string) The name of the new workspace. Must be unique.
      current_snapshot: (string) The current snapshot ID of the workspace,
        used to verify that the workspace hasn't changed. If not None, the
        delete will succeed if and only if the snapshot ID of the workspace
        matches this value.
    """
    request = self.messages.SourceProjectsReposWorkspacesDeleteRequest(
        projectId=self._project_id, repoName=self._repo_name,
        name=workspace_name, currentSnapshotId=current_snapshot)
    self._service.Delete(request)


class Workspace(object):
  """Abstracts a workspace."""

  # Maximum amount of data to buffer/maximum file size. Each modification
  # to the workspace is a single POST request, and anything more than a few
  # hundred KB tends to trigger DEADLINE_EXCEEDED errors. Empirically, 256KB
  # is a good threshold.
  SIZE_THRESHOLD = 256 * 2**10

  def __init__(self, project_id, workspace_name, repo_name='', state=None,
               client=None, messages=None):
    """Initialize from a workspace message.

    Args:
      project_id: (string) The project ID for the workspace.
      workspace_name: (string) The name of the workspace
      repo_name: (string) The repo containing the workspace. If not specified,
        use the default repo for the project.
      state: (messages.Workspace) Server-supplied workspace information.
        Since this argument usually comes from a call to the server, the repo
        will usually be specified by a uid rather than a name.
      client: (apitools.BaseApiService) The API client to use.
      messages: (module) The module containing the API messages to use.
    """
    self._project_id = project_id
    self._repo_name = repo_name
    self._workspace_name = workspace_name
    self._pending_actions = []
    self._workspace_state = state
    self._post_callback = None
    self.client = client or GetClientInstance()
    self.messages = messages or GetMessagesModule(client)
    self._service = self.client.projects_repos_workspaces

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
    request = self.messages.SourceProjectsReposWorkspacesModifyWorkspaceRequest(
        projectId=self._project_id, repoName=self._repo_name,
        name=self._workspace_name,
        modifyWorkspaceRequest=self.messages.ModifyWorkspaceRequest(
            actions=self._pending_actions))
    self._workspace_state = (
        self._service.ModifyWorkspace(request))
    if self._post_callback:
      self._post_callback(len(self._pending_actions))
    self._pending_actions = []

  def WriteFile(self, path, contents, mode=None):
    """Schedule an action to create or modify a file.

    Args:
      path: The path of the file to write.
      contents: The new contents of the file.
      mode: The new mode of the file.
    Raises:
      FileTooBigException: Indicates that the file contents are bigger than the
        maximum size supported by ModifyWorkspace.
    """
    mode = mode or self.messages.WriteAction.ModeValueValuesEnum.NORMAL

    if len(contents) > self.SIZE_THRESHOLD:
      raise FileTooBigException(path, len(contents), self.SIZE_THRESHOLD)

    path = _NormalizeToSourceAPIPath(path)
    self._pending_actions.append(self.messages.Action(
        writeAction=self.messages.WriteAction(
            path=path, contents=contents, mode=mode)))
    self.FlushPendingActions(check_size_threshold=True)
