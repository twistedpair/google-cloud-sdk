# Copyright 2013 Google Inc. All Rights Reserved.
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
"""Common utility functions for the dns tool."""

import functools
import json
import sys

from apitools.base.py import exceptions as apitools_exceptions

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions


def GetError(error, verbose=False):
  """Returns a ready-to-print string representation from the http response.

  Args:
    error: A string representing the raw json of the Http error response.
    verbose: Whether or not to print verbose messages [default false]

  Returns:
    A ready-to-print string representation of the error.
  """
  data = json.loads(error.content)
  reasons = ','.join([x['reason'] for x in data['error']['errors']])
  status = data['error']['code']
  message = data['error']['message']
  code = error.resp.reason
  if verbose:
    PrettyPrint(data)
  return ('ResponseError: status=%s, code=%s, reason(s)=%s\nmessage=%s' %
          (str(status), code, reasons, message))


def GetErrorMessage(error):
  error = json.loads(error.content).get('error', {})
  return '\n{0} (code: {1})'.format(error.get('message', ''), error.get('code',
                                                                        ''))


def HandleHttpError(func):
  """Decorator that catches HttpError and raises corresponding HttpException."""

  @functools.wraps(func)
  def CatchHTTPErrorRaiseHTTPException(*args, **kwargs):
    try:
      return func(*args, **kwargs)
    except apitools_exceptions.HttpError as error:
      msg = GetErrorMessage(error)
      unused_type, unused_value, traceback = sys.exc_info()
      raise exceptions.HttpException, msg, traceback

  return CatchHTTPErrorRaiseHTTPException


def PrettyPrintString(value):
  return json.dumps(value, sort_keys=True, indent=4, separators=(',', ': '))


def PrettyPrint(value):
  print PrettyPrintString(value)


def AppendTrailingDot(name):
  return name if not name or name.endswith('.') else name + '.'


ZONE_FLAG = base.Argument(
    '--zone',
    '-z',
    completion_resource='dns.managedZones',
    help='Name of the managed-zone whose record-sets you want to manage.',
    required=True)
