# -*- coding: utf-8 -*- #
# Copyright 2026 Google LLC. All Rights Reserved.
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
"""Exceptions for Cloud Run compose commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.core import exceptions


class ComposeError(exceptions.Error):
  """Base class for run compose exceptions."""


class GoBinaryError(ComposeError):
  """Error from run-compose Go binary.

  This exception represents all errors originating from the Go binary.
  The exit code and error message are preserved from Go binary's exit code
  and error message.
  Exit codes 0-99 are reserved for errors from the Go binary.
  To find the mapping of exit code to error type, refer to golang binary.
  """

  def __init__(self, message, exit_code):
    super(GoBinaryError, self).__init__(message)
    self.exit_code = exit_code


class GcloudError(ComposeError):
  """Reserved for exceptions in run-compose caused by gcloud.

  Exit codes 100-200 are reserved for this type of error.
  """

  def __init__(self, message, exit_code=100):
    super(GcloudError, self).__init__(message, exit_code=exit_code)


class GcloudResourcesError(ComposeError):
  """Reserved for exceptions in run-compose caused by gcloud resources.

  Exit codes 111-125 are reserved for this type of error.
  """

  def __init__(self, message, exit_code=100):
    super(GcloudResourcesError, self).__init__(message, exit_code=exit_code)


class BuildError(ComposeError):
  """Reserved for exceptions in run-compose caused by build failures.

  Exit codes 126-135 are reserved for this type of error.
  """

  def __init__(self, message, exit_code=100):
    super(BuildError, self).__init__(message, exit_code=exit_code)


class DeployError(ComposeError):
  """Reserved for exceptions in run-compose caused by deployment failures.

  Exit codes 136-145 are reserved for this type of error.
  """

  def __init__(self, message, exit_code=100):
    super(DeployError, self).__init__(message, exit_code=exit_code)
