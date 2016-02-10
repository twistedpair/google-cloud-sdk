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

"""Error support for Cloud Debugger libraries."""

import functools
import json

from googlecloudsdk.core import exceptions
from googlecloudsdk.third_party.apitools.base.py import exceptions as api_exceptions


class NoEndpointError(Exception):

  def __str__(self):
    return (
        'Debug endpoint not initialized. DebugObject.SetApiEndpoint must be '
        'called before using this module.')


class UnknownHttpError(exceptions.Error):
  """An unknown error occurred during a remote API call."""

  def __init__(self, error):
    error_content = json.loads(error.content)['error']
    print 'Error Content is {0}'.format(error_content)
    message = '%s %s' % (error_content['code'], error_content['message'])
    super(UnknownHttpError, self).__init__(message)


def ErrorFromHttpError(error):
  """Returns a more specific error from an HttpError.

  Args:
    error: HttpError resulting from unsuccessful call to API.

  Returns:
    Specific error based on error reason in HttpError.
  """
  # Handle individual errors based error.status_code here as new API calls
  # are added.
  return UnknownHttpError(error)


def HandleHttpError(method=None, error_handler=ErrorFromHttpError):
  """Decorator that catches HttpError and raises corresponding error.

  Args:
    method: The function to decorate.
    error_handler: A function which maps an HttpError to a more meaningful
      app-specific error.
  Returns:
    The decorator function
  """
  if method is None:
    return functools.partial(HandleHttpError, error_handler=error_handler)
  @functools.wraps(method)
  def CatchHTTPErrorRaiseHTTPException(*args, **kwargs):
    try:
      return method(*args, **kwargs)
    except api_exceptions.HttpError as error:
      raise error_handler(error)
  return CatchHTTPErrorRaiseHTTPException
