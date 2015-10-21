# Copyright 2015 Google Inc. All Rights Reserved.

"""Support for source snapshots."""

from datetime import datetime
import os
import uuid
import zipfile

from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io
from googlecloudsdk.shared.source import generate_source_context as contexts
from googlecloudsdk.shared.source import source


# SNAPSHOT_PREFIX is an arbitrary string used to distinguish snapshot workspaces
# from other types of workspaces.
SNAPSHOT_PREFIX = 'google/_snapshot/'

# Snapshots can actually be stored in any repo, but we chose
# google-source-snapshots to keep them separate and avoid cluttering the
# list of workspaces in the default repo. We can revisit this choice at any
# time, since the source context includes the repo name, and the effect of a
# change would simply be that future snapshots would be stored in a different
# repo.
SNAPSHOT_REPO_NAME = 'google-source-snapshots'

# Snapshot names need to be unique, but explicitly-generated snapshots do not
# need to have a predictable name, and there is no reliable human-readable
# identifier for them. For that reason, we generate a uuid string as the primary
# name of an explicit snapshot. Since the string is arbitrary, however, we can
# include some useful information to distinguish it for display, so we use the
# current date and time as a prefix.
TIME_FORMAT = '%Y/%m/%d-%H.%M.%S'


def _IsWorkspaceForSnapshot(workspace_name, snapshot_id):
  return (workspace_name.startswith(SNAPSHOT_PREFIX) and
          workspace_name.endswith(snapshot_id))


class Snapshot(object):
  """Represents a snapshot."""

  def __init__(self, project_id, repo_name, name):
    self.project_id = project_id
    self.repo_name = repo_name
    if name.startswith(SNAPSHOT_PREFIX):
      self.id = name[len(SNAPSHOT_PREFIX):]
    else:
      self.id = name

  def __eq__(self, other):
    return (isinstance(other, self.__class__)
            and self.__dict__ == other.__dict__)

  def __ne__(self, other):
    return not self.__eq__(other)

  def __repr__(self):
    return 'source.snapshots::{0}/{1}/{2}'.format(
        self.project_id, self.repo_name, self.id)

  @property
  def workspace_name(self):
    return SNAPSHOT_PREFIX + self.id


class SnapshotManager(object):
  """Provides methods for manipulating source snapshots."""

  def __init__(self, project_id=None, repo_name=None):
    if not project_id:
      project_id = properties.VALUES.core.project.Get(required=True)
    self._project_id = project_id

    if not repo_name:
      repo_name = SNAPSHOT_REPO_NAME
    self._repo_name = repo_name
    self._repo = None

  def GetSnapshotRepo(self, create_if_missing=True):
    """Returns the repo where snapshots will be created.

    Args:
      create_if_missing: (Boolean) Indicates that the repo should be created if
          it does not exist.
    Returns:
      (Repo) The snapshot repository.
    """

    if self._repo or not create_if_missing:
      return self._repo

    # Verify that the snapshot repo exists, and if not, create it.
    project = source.Project(self._project_id)
    if not project.GetRepo(self._repo_name):
      project.CreateRepo(self._repo_name)
    self._repo = source.Repo(self._project_id, self._repo_name)
    return self._repo

  def _AddSourceDirToWorkspace(self, workspace, src_name, target_root):
    """Add files in the given directory to a workspace.

    Args:
      workspace: (source.Workspace) The workspace to add files to.
      src_name: (string) A directory to snapshot.
      target_root: (string) Root directory of the target tree in the snapshot.
    Returns:
      ([dict], int, int) A 3-tuple containing an array of source contexts,
      the number of files added to the workspace, and the total size of the
      files added.
    """

    src_path = os.path.abspath(src_name)
    source_contexts = []
    # Add context for any external repos.
    try:
      for s in contexts.CalculateExtendedSourceContexts(src_path):
        if s not in source_contexts:
          source_contexts.append(s)
    except contexts.GenerateSourceContextError:
      # We don't care if there's no external source context. We can even
      # snapshot a bunch of local files if necessary.
      pass

    # TODO(danielsb) Once "wsync snapshot" is available, use that instead of
    # explicitly modifying the workspace as we do here.

    paths = [os.path.relpath(os.path.join(basedir, f), src_path)
             for basedir, _, files in os.walk(src_path) for f in files]
    total_files = len(paths)
    progress_bar = console_io.ProgressBar(
        'Uploading {0} files'.format(total_files))
    (read_progress, write_progress) = console_io.ProgressBar.SplitProgressBar(
        progress_bar.SetProgress, [1, 6])
    def UpdateProgress(action_count):
      write_progress((1.0 * action_count) / total_files)
    workspace.SetPostCallback(UpdateProgress)
    progress_bar.Start()

    total_size = 0
    file_count = 0
    contents = None
    for path in paths:
      with open(os.path.join(src_path, path), 'r') as f:
        contents = f.read()
      if contents:
        total_size += len(contents)
        file_count += 1
        read_progress((1.0 * file_count) / total_files)
        workspace.WriteFile(os.path.join(target_root, path), contents)
    return (source_contexts, total_files, total_size)

  def _AddSourceJarToWorkspace(self, workspace, src_name, target_root):
    """Add files in the given source jar to a workspace.

    Args:
      workspace: (source.Workspace) The workspace to add files to.
      src_name: (string) A directory tree or source jar to snapshot.
      target_root: (string) Root directory of the target tree in the snapshot.
    Returns:
      ([dict], int, int) A 3-tuple containing an array of source contexts,
      the number of files added to the workspace, and the total size of the
      files added.
    """

    source_contexts = []
    jar_file = None
    try:
      jar_file = zipfile.ZipFile(src_name, 'r')
      paths = [zi.filename for zi in jar_file.infolist()
               if zi.filename.endswith('.java')]

      total_files = len(paths)
      progress_bar = console_io.ProgressBar(
          'Uploading {0} files'.format(total_files))
      (read_progress, write_progress) = console_io.ProgressBar.SplitProgressBar(
          progress_bar.SetProgress, [1, 6])
      def UpdateProgress(action_count):
        write_progress((1.0 * action_count) / total_files)
      workspace.SetPostCallback(UpdateProgress)
      progress_bar.Start()

      total_size = 0
      file_count = 0
      for path in paths:
        contents = jar_file.read(path)
        if contents:
          total_size += len(contents)
          file_count += 1
          read_progress((1.0 * file_count) / total_files)
          workspace.WriteFile(os.path.join(target_root, path), contents)
    finally:
      if jar_file:
        jar_file.close()
    return (source_contexts, total_files, total_size)

  def UploadSnapshot(self, snapshot_name, src_name, target_root):
    """Create or upload a snapshot of the given directory.

    Args:
      snapshot_name: (string) The name of the snapshot to upload. If empty, a
        name will be generated.
      src_name: (string) A directory tree or source jar to snapshot.
      target_root: (string) Root directory of the target tree in the snapshot.
    Returns:
      A dictionary containing various status information:
        'workspace': The final state of the workspace after the snapshot is
          committed.
        'source_context': A source context pointing to the snapshot.
        'files_written': The number of files written in the snapshot.
        'size_written': The total number of bytes in all files in the snapshot.
    """

    # Source API fails with leading or trailing slashes on file names.
    if target_root:
      target_root = target_root.strip('/')
    workspace = None
    if snapshot_name:
      snapshot = self._FindSnapshot(snapshot_name)
      if snapshot:
        workspace = source.Workspace(
            self._project_id, self._repo_name, snapshot.workspace_name,
            state=self.GetSnapshotRepo().GetWorkspace(snapshot.workspace_name))
    else:
      snapshot_name = (
          datetime.utcnow().strftime(TIME_FORMAT) + '.' + uuid.uuid4().hex)
    if not workspace:
      snapshot = Snapshot(self._project_id, self._repo_name, snapshot_name)
      workspace = self.GetSnapshotRepo().CreateWorkspace(
          snapshot.workspace_name, snapshot.workspace_name)
    return self._PopulateSnapshot(snapshot, workspace, src_name, target_root)

  def _PopulateSnapshot(self, snapshot, workspace, src_name, target_root):
    """Populates a snapshot workspace with the given files.

    Args:
      snapshot: (Snapshot) A snapshot.
      workspace: (source.Workspace) The workspace for the snapshot.
      src_name: (string) A directory tree or source jar to snapshot.
      target_root: (string) Root directory of the target tree in the snapshot.
    Returns:
      A dictionary containing various status information:
        'workspace': The final state of the workspace after the snapshot is
          committed.
        'source_contexts': One or more dictionaries compatible with the
          ExtendedSourceContext message, including one context pointing
          to the snapshot. This context will be the only one with the value
          'snapshot' for its 'category' label.
        'files_written': The number of files written in the snapshot.
        'size_written': The total number of bytes in all files in the snapshot.
    """
    total_size = 0
    total_files = 0
    if os.path.isdir(src_name):
      source_contexts, new_files, new_size = self._AddSourceDirToWorkspace(
          workspace, src_name, target_root)
    else:
      source_contexts, new_files, new_size = self._AddSourceJarToWorkspace(
          workspace, src_name, target_root)
    total_files += new_files
    total_size += new_size
    workspace.FlushPendingActions()
    source_contexts.append({
        'context': {
            'cloudWorkspace': {
                'workspaceId': {
                    'name': snapshot.id,
                    'repoId': {
                        'projectRepoId': {
                            'projectId': self._project_id,
                            'repoName': self._repo_name}}}}},
        'labels': {'category': 'snapshot'}})
    return {
        'snapshot': snapshot,
        'source_contexts': source_contexts,
        'files_written': total_files,
        'size_written': total_size}

  def ListSnapshots(self):
    for ws in self.GetSnapshotRepo().ListWorkspaces():
      if ws.name.startswith(SNAPSHOT_PREFIX):
        yield Snapshot(self._project_id, self._repo_name, ws.name)

  def _FindSnapshot(self, snapshot_id):
    for ws in self.GetSnapshotRepo().ListWorkspaces():
      if _IsWorkspaceForSnapshot(ws.name, snapshot_id):
        return Snapshot(self._project_id, self._repo_name, ws.name)

  def DeleteSnapshot(self, snapshot_id):
    snapshot = self._FindSnapshot(snapshot_id)
    self.GetSnapshotRepo().DeleteWorkspace(snapshot.workspace_name)
    return snapshot
