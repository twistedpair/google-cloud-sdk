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

"""Module for translating HttpErrors into HttpExceptions."""

from functools import wraps
import json
import sys

from apitools.base.py import exceptions as apitools_exceptions

from googlecloudsdk.calliope import exceptions


def GetHttpErrorMessage(error):
  """Returns a human readable string representation from the http response.

  Args:
    error: apitools HttpException representing the error response.

  Returns:
    A human readable string representation of the error.
  """
  code = getattr(error.response, 'status', '')  # Example: 403
  status = ''
  message = ''
  try:
    data = json.loads(error.content)
    if 'error' in data:
      error_info = data['error']
      code = error_info.get('code', code)  # Example: 403
      status = error_info.get('status', '')  # Example: PERMISSION_DENIED
      message = error_info.get('message', '')
  except (ValueError, TypeError):
    message = error.content
  if not status and not message:
    # Example: 'HTTPError 403'
    return 'HTTPError {0}'.format(code)
  if not status or not message:
    # Example: 'PERMISSION_DENIED' or 'You do not have permission to access X'
    return '{0}'.format(status or message)
  # Example: 'PERMISSION_DENIED: You do not have permission to access X'
  return '{0}: {1}'.format(status, message)


def HandleHttpErrors(func):
  """Decorator that catches apitools HttpError and raises HttpException."""

  @wraps(func)
  def CatchHTTPErrorRaiseHTTPExceptionFn(*args, **kwargs):
    """Catch HTTPError and raise HTTPException for normal functions."""
    try:
      return func(*args, **kwargs)
    except apitools_exceptions.HttpError as error:
      msg = GetHttpErrorMessage(error)
      unused_type, unused_value, traceback = sys.exc_info()
      raise exceptions.HttpException, msg, traceback

  @wraps(func)
  def CatchHTTPErrorRaiseHTTPExceptionGen(*args, **kwargs):
    """Catch HTTPError and raise HTTPException for generator functions."""
    try:
      result = func(*args, **kwargs)
      for element in result:
        yield element
    except apitools_exceptions.HttpError as error:
      msg = GetHttpErrorMessage(error)
      unused_type, unused_value, traceback = sys.exc_info()
      raise exceptions.HttpException, msg, traceback

  # The wrapper should only be used with functions or methods.
  # Technically, the proper way is to check isinstance of MethodType or
  # FunctionType. However, we want to make this fast, and we want it to fail
  # for classes (which can be callable or implement __call__!). func_code is
  # also used below to check if it's a generator so it needs to exist.
  if not hasattr(func, 'func_code'):
    raise TypeError('CatchHTTPErrorRaiseHTTPException can only be applied to '
                    'functions or methods.')

  # Check if function is a generator.
  # This is basically an inline implementation of inspect.isgeneratorfunction
  # so we won't have to import inspect. Importing inspect caused perf problems
  # in the past. 0x20 is defined as CO_GENERATOR in inspect module.
  if func.func_code.co_flags & 0x20:
    return CatchHTTPErrorRaiseHTTPExceptionGen
  return CatchHTTPErrorRaiseHTTPExceptionFn
