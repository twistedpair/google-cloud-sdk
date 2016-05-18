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

"""Support for source captures."""

from datetime import datetime
import os
import re
import uuid
import zipfile
from googlecloudsdk.api_lib.source import git
from googlecloudsdk.api_lib.source import source
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io
from googlecloudsdk.third_party.appengine.tools import context_util as contexts

# CAPTURE_PREFIX is an arbitrary string used to distinguish capture workspaces
# from other types of workspaces.
CAPTURE_PREFIX = 'google/_capture/'

# Captures can actually be stored in any repo, but we chose
# google-source-captures to keep them separate and avoid cluttering the
# list of workspaces in the default repo. We can revisit this choice at any
# time, since the source context includes the repo name, and the effect of a
# change would simply be that future captures would be stored in a different
# repo.
CAPTURE_REPO_NAME = 'google-source-captures'

# Capture names need to be unique, but explicitly-generated captures do not
# need to have a predictable name, and there is no reliable human-readable
# identifier for them. For that reason, we generate a uuid string as the primary
# name of an explicit capture. Since the string is arbitrary, however, we can
# include some useful information to distinguish it for display, so we use the
# current date and time as a prefix.
TIME_FORMAT = '%Y/%m/%d-%H.%M.%S'


def _IsWorkspaceForCapture(workspace_name, capture_id):
  return (workspace_name.startswith(CAPTURE_PREFIX) and
          workspace_name.endswith(capture_id))


class Capture(object):
  """Represents a capture."""

  def __init__(self, project_id, repo_name, name):
    self.project_id = project_id
    self.repo_name = repo_name
    if name.startswith(CAPTURE_PREFIX):
      self.id = name[len(CAPTURE_PREFIX):]
    else:
      self.id = name

  def __eq__(self, other):
    return (isinstance(other, self.__class__)
            and self.__dict__ == other.__dict__)

  def __ne__(self, other):
    return not self.__eq__(other)

  def __repr__(self):
    return 'source.captures::{0}/{1}/{2}'.format(
        self.project_id, self.repo_name, self.id)

  @property
  def workspace_name(self):
    return CAPTURE_PREFIX + self.id


class CaptureManager(object):
  """Provides methods for manipulating source captures."""

  def __init__(self, project_id=None, repo_name=None):
    if not project_id:
      project_id = properties.VALUES.core.project.Get(required=True)
    self._project_id = project_id

    if not repo_name:
      repo_name = CAPTURE_REPO_NAME
    self._repo_name = repo_name
    self._repo = None
    self._ignore_handler = git.GitIgnoreHandler()
    # Add a top-level ignore for the .git directory (the expression matches
    # the .git directory and any file contained in it).
    self._ignore_handler.AddIgnoreRules(
        '/', [(re.compile(r'^(.*/)?\.git(/.*)?'), True)])

  def GetCaptureRepo(self, create_if_missing=True):
    """Returns the repo where captures will be created.

    Args:
      create_if_missing: (Boolean) Indicates that the repo should be created if
          it does not exist.
    Returns:
      (Repo) The capture repository.
    """

    if self._repo or not create_if_missing:
      return self._repo

    # Verify that the capture repo exists, and if not, create it.
    project = source.Project(self._project_id)
    if not project.GetRepo(self._repo_name):
      project.CreateRepo(self._repo_name)
    self._repo = source.Repo(self._project_id, self._repo_name)
    return self._repo

  def _AddSourceDirToWorkspace(self, workspace, src_name, target_root):
    """Add files in the given directory to a workspace.

    Args:
      workspace: (source.Workspace) The workspace to add files to.
      src_name: (string) A directory to capture.
      target_root: (string) Root directory of the target tree in the capture.
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
      # capture a bunch of local files if necessary.
      pass

    # TODO(user) Once "wsync capture" is available, use that instead of
    # explicitly modifying the workspace as we do here.

    paths = [os.path.relpath(f, src_path)
             for f in self._ignore_handler.GetFiles(src_path)
             if not os.path.islink(f)]
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
        try:
          workspace.WriteFile(os.path.join(target_root, path), contents)
        except source.FileTooBigException as e:
          log.warning(e)
    return (source_contexts, total_files, total_size)

  def _AddSourceJarToWorkspace(self, workspace, src_name, target_root):
    """Add files in the given source jar to a workspace.

    Args:
      workspace: (source.Workspace) The workspace to add files to.
      src_name: (string) A directory tree or source jar to capture.
      target_root: (string) Root directory of the target tree in the capture.
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

  def UploadCapture(self, capture_name, src_name, target_root):
    """Create or upload a capture of the given directory.

    Args:
      capture_name: (string) The name of the capture to upload. If empty, a
        name will be generated.
      src_name: (string) A directory tree or source jar to capture.
      target_root: (string) Root directory of the target tree in the capture.
    Returns:
      A dictionary containing various status information:
        'workspace': The final state of the workspace after the capture is
          committed.
        'source_context': A source context pointing to the capture.
        'files_written': The number of files written in the capture.
        'size_written': The total number of bytes in all files in the capture.
    """

    # Source API fails with leading or trailing slashes on file names.
    if target_root:
      target_root = target_root.strip('/')
    workspace = None
    if capture_name:
      capture = self._FindCapture(capture_name)
      if capture:
        workspace = source.Workspace(
            self._project_id, capture.workspace_name,
            repo_name=self._repo_name,
            state=self.GetCaptureRepo().GetWorkspace(capture.workspace_name))
    else:
      capture_name = (
          datetime.utcnow().strftime(TIME_FORMAT) + '.' + uuid.uuid4().hex)
    if not workspace:
      capture = Capture(self._project_id, self._repo_name, capture_name)
      workspace = self.GetCaptureRepo().CreateWorkspace(
          capture.workspace_name, capture.workspace_name)
    return self._PopulateCapture(capture, workspace, src_name, target_root)

  def _PopulateCapture(self, capture, workspace, src_name, target_root):
    """Populates a capture workspace with the given files.

    Args:
      capture: (Capture) A capture.
      workspace: (source.Workspace) The workspace for the capture.
      src_name: (string) A directory tree or source jar to capture.
      target_root: (string) Root directory of the target tree in the capture.
    Returns:
      A dictionary containing various status information:
        'workspace': The final state of the workspace after the capture is
          committed.
        'source_contexts': One or more dictionaries compatible with the
          ExtendedSourceContext message, including one context pointing
          to the capture. This context will be the only one with the value
          'capture' for its 'category' label.
        'files_written': The number of files written in the capture.
        'size_written': The total number of bytes in all files in the capture.
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
                    'name': capture.id,
                    'repoId': {
                        'projectRepoId': {
                            'projectId': self._project_id,
                            'repoName': self._repo_name}}}}},
        'labels': {'category': 'capture'}})
    return {
        'capture': capture,
        'source_contexts': source_contexts,
        'files_written': total_files,
        'size_written': total_size}

  def ListCaptures(self):
    for ws in self.GetCaptureRepo().ListWorkspaces():
      if ws.name.startswith(CAPTURE_PREFIX):
        yield Capture(self._project_id, self._repo_name, ws.name)

  def _FindCapture(self, capture_id):
    for ws in self.GetCaptureRepo().ListWorkspaces():
      if _IsWorkspaceForCapture(ws.name, capture_id):
        return Capture(self._project_id, self._repo_name, ws.name)

  def DeleteCapture(self, capture_id):
    capture = self._FindCapture(capture_id)
    self.GetCaptureRepo().DeleteWorkspace(capture.workspace_name)
    return capture
