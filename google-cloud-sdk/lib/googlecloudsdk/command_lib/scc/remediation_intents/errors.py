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
"""Custom errors for the SCC RemediationIntent resource commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from googlecloudsdk.core import exceptions


class Error(exceptions.Error):
  """Base error class for this module."""


class TfStateFetchingError(Error):
  """An error occurred while fetching the TfState data."""

  def __init__(self, error_message: str):
    """Initializes the TfStateFetchingError.

    Args:
      error_message: The error message to be included in the exception.
    """
    if error_message is None:
      super(Error, self).__init__(
          'An error occurred while fetching the TfState data'
      )
    else:
      super(Error, self).__init__(
          f'An error occurred while fetching the TfState data: {error_message}'
      )


class APICallError(Error):
  """An error occurred while calling the RemediationIntent API."""

  def __init__(self, method_name: str, error_message: str):
    """Initializes the APICallError.

    Args:
      method_name: The name of the API method that failed.
      error_message: The error message to be included in the exception.
    """
    if error_message is None or method_name is None:
      super(Error, self).__init__(
          'An Internal service error occurred while calling the method'
      )
    else:
      super(Error, self).__init__(
          'An Internal service error occurred while calling the method'
          f' {method_name}, detailed error: {error_message}'
      )


class InvalidGitConfigError(Error):
  """An error representing missing field in the git config file."""

  def __init__(self, missing_field: str = None):
    """Initializes the InvalidGitConfigError.

    Args:
      missing_field: The name of the missing field in the git config file.
    """
    if missing_field is None:
      super(Error, self).__init__('Missing git config field name.')
    else:
      super(Error, self).__init__(
          f'Field missing from the git config file: {missing_field}.'
      )


class InvalidDirectoryPathError(Error):
  """An error representing an invalid relative directory path."""

  def __init__(self, dir_path: str, error_message: str):
    """Initializes the InvalidDirectoryPathError.

    Args:
      dir_path: The invalid relative directory path.
      error_message: The error message to be included in the exception.
    """
    if dir_path is None:
      super().__init__('Invalid relative directory path.')
    else:
      super().__init__(
          f'Invalid relative directory path: {dir_path}. Detailed error:'
          f' {error_message}'
      )
