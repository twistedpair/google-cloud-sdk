# Copyright 2015 Google Inc. All Rights Reserved.
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

"""Common utility functions for sql errors and exceptions."""

import json
import sys

from apitools.base.py import exceptions

from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.core import exceptions as core_exceptions


class OperationError(core_exceptions.Error):
  pass


def GetErrorMessage(error):
  error_obj = json.loads(error.content).get('error', {})
  errors = error_obj.get('errors', [])
  debug_info = errors[0].get('debugInfo', '') if len(errors) else ''
  return (error_obj.get('message', '') +
          ('\n' + debug_info if debug_info is not '' else ''))


def ReraiseHttpException(foo):
  def Func(*args, **kwargs):
    try:
      return foo(*args, **kwargs)
    except exceptions.HttpError as error:
      msg = GetErrorMessage(error)
      unused_type, unused_value, traceback = sys.exc_info()
      raise calliope_exceptions.HttpException, msg, traceback
  return Func
