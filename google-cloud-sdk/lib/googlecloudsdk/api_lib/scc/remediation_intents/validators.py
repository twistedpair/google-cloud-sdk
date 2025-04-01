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
"""Module for storing the functions related to validation of data."""

import pathlib
from typing import Any, Mapping

from googlecloudsdk.command_lib.scc.remediation_intents import errors


def validate_git_config(git_config_file: Mapping[str, Any]):
  """Validates the git config file, raises an error if it is invalid.

  Args:
    git_config_file: The git config file data in dict format to be validated.
  """
  # Check if the required fields are present in the git config file.
  # The fields are: [remote, main-branch-name, branch-prefix]
  if git_config_file.get('remote', None) is None:
    raise errors.InvalidGitConfigError('remote')

  if git_config_file.get('main-branch-name', None) is None:
    raise errors.InvalidGitConfigError('main-branch-name')

  if git_config_file.get('branch-prefix', None) is None:
    raise errors.InvalidGitConfigError('branch-prefix')

  if git_config_file.get('reviewers', None) is None:
    raise errors.InvalidGitConfigError('reviewers')


def validate_relative_dir_path(rel_dir_path: str):
  """Validates the relative directory path, raises an error if it is invalid.

  Args:
    rel_dir_path: The relative directory path to be validated.
  """
  # Default to current directory if empty
  rel_dir_path = rel_dir_path.strip() or '.'
  path_obj = pathlib.Path(rel_dir_path)

  if path_obj.is_absolute():
    raise errors.InvalidDirectoryPathError(
        rel_dir_path, 'Directory path must be relative not absolute.'
    )
  if not path_obj.exists():
    raise errors.InvalidDirectoryPathError(
        rel_dir_path, 'Directory path does not exist.'
    )
  if not path_obj.is_dir():
    raise errors.InvalidDirectoryPathError(
        rel_dir_path, 'Given path is not a directory.'
    )
