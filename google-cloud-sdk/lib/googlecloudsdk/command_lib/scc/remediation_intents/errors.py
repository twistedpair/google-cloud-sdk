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
