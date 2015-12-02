# Copyright 2015 Google Inc. All Rights Reserved.

"""Source apis layer."""
import os

from googlecloudsdk.core import properties
from googlecloudsdk.third_party.apis.source.v1 import source_v1_messages as messages
from googlecloudsdk.third_party.apis.source.v1.source_v1_client import SourceV1 as client
from googlecloudsdk.third_party.apitools.base.py import exceptions
from googlecloudsdk.third_party.apitools.base.py import list_pager


def _NormalizeToSourceAPIPath(path):
  """Fix an OS-native path to conform to the Unix/Source API style.

  Args:
    path: (string) An OS-native path (e.g. "/foo/bar" on Unix or "foo\bar" on
      Windows.
  Returns:
    (string) The path converted to Unix/Source API style. '\' characters will
    be converted to '/' on Windows.
    TODO(danielsb) Consider whether it makes sense to strip drive letters.
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


class Source(object):
  """Base class for source api wrappers."""
  _client = None
  _resource_parser = None

  def _CheckClient(self):
    if not self._client:
      raise NoEndpointException()

  @classmethod
  def SetApiEndpoint(cls, http, endpoint):
    cls._client = client(url=endpoint, get_credentials=False, http=http)

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
    return self._client.projects_repos.List(request).repos

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


class Repo(Source):
  """Abstracts a source repository.

  TODO(danielsb) Increase coverage of the API.
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

  def ListRevisions(
      self, starts=None, ends=None, path=None,
      walk_direction=messages.SourceProjectsReposRevisionsListRequest.
      WalkDirectionValueValuesEnum.FORWARD):
    """Request a list of revisions.

    Args:
      starts: ([string])
        Revision IDs (hexadecimal strings) that specify where the listing
        begins. If empty, the repo heads (revisions with no children) are
        used.
      ends: ([string])
        Revision IDs (hexadecimal strings) that specify where the listing
        ends. If this field is present, the listing will contain only
        revisions that are topologically between starts and ends, inclusive.
      path: (string)
        List only those revisions that modify path.
      walk_direction: (messages.SourceProjectsReposRevisionsListRequest.
                       WalkDirectionValueValuesEnum)
        The direction to walk the graph.
    Returns:
      [messages.Revision] The revisions matching the search criteria, in the
      order specified by walkDirection.
    """
    if not starts:
      starts = []
    if not ends:
      ends = []
    if path:
      path = _NormalizeToSourceAPIPath(path)
    request = messages.SourceProjectsReposRevisionsListRequest(
        projectId=self._project_id, repoName=self._repo_name,
        starts=starts, ends=ends, path=path, walkDirection=walk_direction)

    return list_pager.YieldFromList(
        self._client.projects_repos_revisions, request,
        field='revisions', batch_size_attribute='pageSize')

  def ListAliases(self, kind=messages.SourceProjectsReposAliasesListRequest.
                  KindValueValuesEnum.ANY):
    """Request a list of aliases.

    Args:
      kind: (messages.SourceProjectsReposAliasesListRequest.KindValueValuesEnum)
        The type of alias to list (fixed, movable, etc).
    Returns:
      [messages.Alias] The aliases of the given kind.
    """
    request = messages.SourceProjectsReposAliasesListRequest(
        projectId=self._project_id, repoName=self._repo_name, kind=kind)

    return list_pager.YieldFromList(
        self._client.projects_repos_aliases, request,
        field='aliases', batch_size_attribute='pageSize')

  def ListWorkspaces(self):
    """Request a list of workspaces.

    Yields:
      (Workspace) The list of workspaces.
    """
    request = messages.SourceProjectsReposWorkspacesListRequest(
        projectId=self._project_id, repoName=self._repo_name)
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

  def CreateAlias(self, name, revision_id, kind):
    """Create a new alias (branch) in the repo.

    Args:
      name: (string) The name of the branch.
      revision_id: (string) The ID of the revision.
      kind: (messages.Alias.KindValueValuesEnum) The type of alias.
    Returns:
      (messages.Alias) The alias that was created.
    """
    request = messages.SourceProjectsReposAliasesCreateRequest(
        projectId=self._project_id, repoName=self._repo_name,
        alias=messages.Alias(name=name, revisionId=revision_id, kind=kind))
    return self._client.projects_repos_aliases.Create(request)

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

  def Commit(self, message, paths=None):
    """Commit all pending changes to the repo.

    Args:
      message: (string) A description of the commit.
      paths: ([string]) Restrict the commit to the given paths.
    Returns:
      A messages.Workspace object describing the state after the commit.
    """

    self.FlushPendingActions()
    current_snapshot = None
    if self._workspace_state:
      current_snapshot = self._workspace_state.currentSnapshotId
    if not paths:
      paths = []
    else:
      paths = [_NormalizeToSourceAPIPath(path) for path in paths]
    request = messages.SourceProjectsReposWorkspacesCommitWorkspaceRequest(
        projectId=self._project_id, repoName=self._repo_name,
        name=self._workspace_name,
        commitWorkspaceRequest=messages.CommitWorkspaceRequest(
            author=properties.VALUES.core.account.Get(required=True),
            currentSnapshotId=current_snapshot,
            message=message,
            paths=paths))
    self._workspace_state = (
        self._client.projects_repos_workspaces.CommitWorkspace(request))
    return self._workspace_state

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
