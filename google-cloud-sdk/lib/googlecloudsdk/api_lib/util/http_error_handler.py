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

import functools
import json

from googlecloudsdk.calliope import exceptions as base_exceptions
from googlecloudsdk.third_party.apitools.base.py import exceptions as apitools_exceptions


def GetHttpErrorMessage(error):
  """Returns a human readable string representation from the http response.

  Args:
    error: HttpException representing the error response.

  Returns:
    A human readable string representation of the error.
  """
  data = json.loads(error.content)
  code = data['error']['code']
  message = data['error']['message']
  return 'ResponseError: code={0}, message={1}'.format(code, message)


def HandleHttpErrors(func):
  """Decorator that catches HttpErrors and raises a CLI friendly exception."""

  @functools.wraps(func)
  def HandleErrorFn(*args, **kwargs):
    try:
      return func(*args, **kwargs)
    except apitools_exceptions.HttpError as error:
      raise base_exceptions.HttpException(GetHttpErrorMessage(error))

  return HandleErrorFn
