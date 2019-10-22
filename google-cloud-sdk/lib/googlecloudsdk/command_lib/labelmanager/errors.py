# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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
"""Label manager exception utilities."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.core import exceptions as core_exceptions


class Error(core_exceptions.Error):
  """Errors raised by Label Manager commands."""


class LabelKeyCreateError(Error):
  """Errors raised when creating a label key."""


class OperationFailedException(core_exceptions.Error):
  """Class for errors raised when a polled operation completes with an error."""

  def __init__(self, operation_with_error):
    error_code = operation_with_error.error.code
    error_message = operation_with_error.error.message
    message = 'Operation [{0}] failed: {1}: {2}'.format(
        operation_with_error.name, error_code, error_message)
    super(OperationFailedException, self).__init__(message)
