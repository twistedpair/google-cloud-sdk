# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Helper functions to interact with git and github for remediation intents orchestration."""

import os
import subprocess
import tempfile
from typing import Mapping, Tuple

from googlecloudsdk.api_lib.scc.remediation_intents import const
from googlecloudsdk.command_lib.code import run_subprocess
from googlecloudsdk.core.util import files


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
      check=False,
      cwd=os.getcwd(),
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      text=True,
  )  # Output: <256hash> refs/heads/branch_name | empty string if not found.
  return bool(result.stdout.strip())


def get_working_tree_dir(*, remote_name, branch_name):
  """Returns the working tree directory for the branch.

     Will create a new working tree if one doesn't exist

  Args:
    remote_name: Name of the remote of the repo at which to check.
    branch_name: Name of the branch for which the working tree directory is
      required.

  Returns:
    Working tree directory path for the branch in string format.
  """
  worktree_dir = None
  # Check if there is a worktree already for the branch.
  existing_worktrees = subprocess.check_output(
      ['git', 'worktree', 'list']  # output format is: <path> <branch>
  ).decode('utf-8')
  for line in existing_worktrees.splitlines():
    if branch_name in line:
      # If worktree found for the branch, set it
      worktree_dir = line.split()[0]
      break
  if worktree_dir is None:  # else create a new worktree
    worktree_dir = tempfile.mkdtemp()
    subprocess.run(
        ['git', 'worktree', 'add', worktree_dir, '-B', branch_name],
        check=True, cwd=os.getcwd(),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    # Check if the branch exists in the remote and push the branch if not.
    if not branch_remote_exists(remote_name, branch_name):
      subprocess.run(
          ['git', 'push', '--set-upstream', remote_name, branch_name],
          check=False, cwd=worktree_dir,
          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
      )
    # Pull the latest changes from the remote for the branch.
    subprocess.run(
        ['git', 'pull'],
        check=False, cwd=worktree_dir,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
  return worktree_dir


def push_commit(files_data, commit_message, remote_name, branch_name):
  """Pushes the commit to the given branch with the given files data and commit message.

  Args:
    files_data: Dictionary of file path (relative path of the files in original
      repo) and file data in string format to be written
    commit_message: Message to be added to the commit.
    remote_name: Name of the remote of the repo at which to check.
    branch_name: Name of the branch where commit needs to be pushed.
  """
  worktree_dir = get_working_tree_dir(
      remote_name=remote_name, branch_name=branch_name
  )
  # Overwrite the files in the worktree dir's for the branch.
  for file_path, file_data in files_data.items():
    abs_file_path = os.path.join(worktree_dir, file_path)
    files.WriteFileContents(abs_file_path, file_data)
    subprocess.run(  # add them to the git index
        ['git', 'add', abs_file_path],
        check=True,
        cwd=worktree_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

  subprocess.run(
      ['git', 'commit', '-m', commit_message],
      check=False,
      cwd=worktree_dir,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
  )
  # Push the commit.
  subprocess.run(
      ['git', 'push'],
      check=False,
      cwd=worktree_dir,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
  )


def create_pr(
    title, desc, remote_name, branch_name, base_branch, reviewers
) -> Tuple[bool, str]:
  """Creates a PR for the given branch to the main base branch.

  Args:
    title: PR title
    desc: PR description
    remote_name: Name of the remote of the repo at which to check.
    branch_name: The branch from which PR needs to be created.
    base_branch: The main branch name to be which PR needs to be merged.
    reviewers: List of reviewers to be added to the PR.

  Returns:
    Boolean indicating whether the PR was created successfully or not.
    PR link if created successfully, otherwise error message.
  """
  worktree_dir = get_working_tree_dir(
      remote_name=remote_name,
      branch_name=branch_name
  )
  pr_command = [
      'gh',
      'pr',
      'create',
      '--base',
      base_branch,
      '--head',
      branch_name,
      '--title',
      title,
      '--body',
      desc,
      '--assignee',
      reviewers,
  ]
  try:
    p = subprocess.run(  # If successful, output will be the PR link.
        pr_command,
        check=True,
        cwd=worktree_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    pr_link = p.stdout.strip()
  except subprocess.CalledProcessError as e:
    return False, const.PR_FAILURE_MSG.format(stdout=e.stdout, stderr=e.stderr)

  subprocess.run(  # cleanup the worktree
      ['git', 'worktree', 'remove', '--force', worktree_dir],
      check=False,
      cwd=worktree_dir,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
  )
  return True, pr_link


def get_file_modifiers(
    files_data: Mapping[str, str], first: bool = False
) -> Mapping[str, str]:
  """Returns the first (creators) or last modifiers for the given files.

  By default, it returns the last modifiers.

  Args:
    files_data: Dictionary of file path and file contents.
    first: If True, returns the first modifiers for the files. Otherwise,
      returns the last modifiers for the files.

  Returns:
    A dictionary of file path and the modifiers for the given files. If the
    command fails, an empty dictionary is returned. ["file_path" : "modifier"]
  """
  file_modifiers = {}
  base_cmd = [
      'git', 'log',
      *(['--reverse'] if first else []),
      '-s', '-n1', '--pretty=format:%ae%n',
  ]  # By default, the cmd gives the last modifier for the file.
  try:
    for file_path, _ in files_data.items():
      cmd = base_cmd + [file_path]
      # If successful, cmd_output: <email_address> followed by \n
      file_modifiers[file_path] = run_subprocess.GetOutputLines(
          cmd, timeout_sec=const.TF_CMD_TIMEOUT, strip_output=True
      )[0]  # first line of the output is the email address.
    return file_modifiers
  except subprocess.CalledProcessError:
    return {}
