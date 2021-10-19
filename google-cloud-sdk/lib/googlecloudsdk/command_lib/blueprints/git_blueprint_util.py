# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Support library to handle the git blueprint sources."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re


def _ParseGitRepoPath(repo, subdir):
  """Parses a Git repo path and subdirectory.

  Args:
    repo: string, a Git repo path.
    subdir: optional string. The directory within the Git repo to use.

  Returns:
    (string, string, string), a tuple of the Git repository, Git ref, and
    subdirectory
  """
  git_ref = ''
  git_repo = repo

  # If "source" represents a Git URL with "@{ref}" at the end, then parse out
  # the repo and ref parts.
  match = re.search(r'^([^@]+)@(.*)$', git_repo)
  if match:
    git_repo = match.group(1)
    git_ref = match.group(2)

  # For CSR repos it's possible the subdirectory is part of the repo path and
  # needs to be parsed out.
  match = re.search(
      r'(https?://source.developers.google.com/p/[^/]+/r/[^/]+)/(.+)', git_repo)
  if match:
    git_repo = match.group(1)
    if not subdir:
      subdir = match.group(2)
  return git_repo, git_ref, subdir


def GetBlueprintTargetForGit(messages, git_target, git_target_subdir='.'):
  """Returns the GitTarget representation of a blueprint git target.

  Args:
    messages: ModuleType, the messages module that lets us form blueprints API
      messages based on our protos.
    git_target: string, a Git repo path.
    git_target_subdir: optional string. The directory within the Git repo to
      use.

  Returns: a messages.GitTarget
  """
  git_repo, git_branch, git_subdir = _ParseGitRepoPath(git_target,
                                                       git_target_subdir)
  return messages.GitTarget(
      repo=git_repo, branch=git_branch, directory=git_subdir)


def GetBlueprintSourceForGit(messages, source, source_git_subdir=''):
  """Returns the GitSource representation of a blueprint source.

  Args:
    messages: ModuleType, the messages module that lets us form blueprints API
      messages based on our protos.
    source: string, a Git repo path.
    source_git_subdir: optional string. If "source" represents a Git repo, then
      this argument represents the directory within that Git repo to use.

  Returns: a messages.GitSource
  """

  git_repo, git_ref, git_subdir = _ParseGitRepoPath(source, source_git_subdir)
  return messages.GitSource(
      repo=git_repo, ref=git_ref, directory=git_subdir)
