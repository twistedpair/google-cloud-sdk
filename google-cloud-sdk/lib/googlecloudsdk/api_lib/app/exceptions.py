# Copyright 2016 Google Inc. All Rights Reserved.
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

"""This module holds exceptions raised by api lib."""


from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.core import exceptions


class Error(exceptions.Error):
  """Base error for this module."""


class NotFoundError(Error):
  """Raised when the requested resource does not exist."""

  def __init__(self):
    super(exceptions.Error,
          self).__init__('The requested resource was not found.')


class ConflictError(Error):
  """Raised when a new resource already exists."""

  def __init__(self):
    super(exceptions.Error,
          self).__init__('The requested resource already exists.')


class ConfigError(Error):
  """Raised when unable to parse a config file."""

  def __init__(self, message=None, **kwargs):
    message = message or 'Config Error.'
    super(ConfigError, self).__init__(message, **kwargs)


# TODO(b/34516298): use generic HttpException when compatible with v2.
class HttpException(calliope_exceptions.HttpException):
  """Wrapper for HttpException with custom message to include details."""

  def __init__(self, error, error_format=None, error_message=''):
    super(HttpException, self).__init__(error, error_format)
    self.error_message = error_message

  def __str__(self):
    no_details_message = super(HttpException, self).__str__()
    if self.error_message:
      return self.error_message
    return no_details_message

STATUS_CODE_TO_ERROR = {
    404: NotFoundError,
    409: ConflictError
}
