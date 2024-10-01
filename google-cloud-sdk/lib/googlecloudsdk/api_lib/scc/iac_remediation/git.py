# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Helper functions to interact with git and github for iac remediation."""

import os
import subprocess
import tempfile

from googlecloudsdk.command_lib.scc.iac_remediation import errors
from googlecloudsdk.core.util import files


def validate_git_config(git_config_file):
  """Validates the git config file."""
  if git_config_file['remote'] is None:
    raise errors.InvalidGitConfigError('remote')

  if git_config_file['main-branch-name'] is None:
    raise errors.InvalidGitConfigError('main-branch-name')

  if git_config_file['branch-prefix'] is None:
    raise errors.InvalidGitConfigError('branch-prefix')


def is_git_repo():
  """Check whether the current directory is a git repo or not.

  Returns:
    True, repo_root_path if the current directory is a git repo
    False, None otherwise.
  """
  try:
    git_check_cmd = ('git rev-parse --show-toplevel')
    result = subprocess.run(
        git_check_cmd,
        shell=True, check=True, cwd=os.getcwd(),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True,
    )
    return True, result.stdout.strip()
  except subprocess.CalledProcessError:
    return False, None


def branch_remote_exists(remote_name, branch_name):
  """Helper function to check if a branch exists in the remote.

  Args:
    remote_name: Name of the remote of the repo at which to check.
    branch_name: Name of the branch to check.

  Returns:
    Boolean indicating whether the branch exists in the remote.
  """
  result = subprocess.run(
      ['git', 'ls-remote', '--heads', remote_name, branch_name],
      check=False, cwd=os.getcwd(),
      stdout=subprocess.PIPE, stderr=subprocess.PIPE,
      text=True
  )
  return bool(result.stdout.strip())


def get_working_tree_dir(remote_name, branch_name):
  """Returns the working tree directory for the branch.

  Args:
    remote_name: Name of the remote of the repo at which to check.
    branch_name: Name of the branch for which the working tree directory is
    required.

  Returns:
    Working tree directory path for the branch.
  """
  worktree_dir = None
  # check if there is a worktree already for the branch
  existing_worktrees = subprocess.check_output(
      ['git', 'worktree', 'list']  # output format is: <path> <branch>
  ).decode('utf-8')
  for line in existing_worktrees.splitlines():
    if branch_name in line:
      # if worktree found for the branch, set it,
      worktree_dir = line.split()[0]
      break
  if worktree_dir is None:  # else create a new worktree
    worktree_dir = tempfile.mkdtemp()
    subprocess.run(
        ['git', 'worktree', 'add', worktree_dir, '-B', branch_name],
        check=True, cwd=os.getcwd(),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    # check if the branch exists in the remote and push the branch if not
    if not branch_remote_exists(remote_name, branch_name):
      subprocess.run(
          ['git', 'push', '--set-upstream', remote_name, branch_name],
          check=False, cwd=worktree_dir,
          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
      )
    # pull the latest changes from the remote for the branch
    subprocess.run(
        ['git', 'pull'],
        check=False, cwd=worktree_dir,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
  return worktree_dir


def push_commit(files_data, commit_message, remote_name, branch_name):
  """Pushes the commit to the given branch with the given files data and commit message.

  Args:
    files_data: Dictionary of file path (absolute path of the files in original
    repo) and file data to be written
    commit_message: Message to be added to the commit
    remote_name: Name of the remote of the repo at which to check.
    branch_name: Name of the branch where commit needs to be pushed
  """
  is_repo_flag, repo_root_dir = is_git_repo()
  del is_repo_flag
  worktree_dir = get_working_tree_dir(remote_name, branch_name)
  # overwrite the files in the worktree dir's for the branch
  for file_path, file_data in files_data.items():
    rel_path = os.path.relpath(file_path, repo_root_dir)
    abs_file_path = os.path.join(worktree_dir, rel_path)
    files.WriteFileContents(abs_file_path, file_data)
    subprocess.run(  # add them to the git index
        ['git', 'add', abs_file_path],
        check=True, cwd=worktree_dir,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )

  subprocess.run(
      ['git', 'commit', '-m', commit_message],
      check=False, cwd=worktree_dir,
      stdout=subprocess.PIPE, stderr=subprocess.PIPE,
  )
  # push the commit
  subprocess.run(
      ['git', 'push'],
      check=False, cwd=worktree_dir,
      stdout=subprocess.PIPE, stderr=subprocess.PIPE,
  )


def raise_pr(pr_title, pr_desc, remote_name, branch_name, base_branch):
  """Creates a PR for the given branch to the main base branch.

  Args:
    pr_title: PR title
    pr_desc: PR description
    remote_name: Name of the remote of the repo at which to check.
    branch_name: The branch from which PR needs to be created.
    base_branch: The main branch name to be which PR needs to be merged.
  """
  worktree_dir = get_working_tree_dir(remote_name, branch_name)
  pr_command = (
      f'gh pr create --base {base_branch} --head {branch_name} --title'
      f' "{pr_title}" --body "{pr_desc}"'
  )
  subprocess.run(  # create a PR
      pr_command, shell=True, check=False, cwd=worktree_dir,
      stdout=subprocess.PIPE, stderr=subprocess.PIPE,
  )
  subprocess.run(  # cleanup the worktree
      ['git', 'worktree', 'remove', '--force', worktree_dir],
      check=False, cwd=worktree_dir,
      stdout=subprocess.PIPE, stderr=subprocess.PIPE,
  )
