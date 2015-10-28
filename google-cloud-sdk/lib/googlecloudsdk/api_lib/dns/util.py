# Copyright 2013 Google Inc. All Rights Reserved.
"""Common utility functions for the dns tool."""

import functools
import json
import sys

from googlecloudsdk.calliope import exceptions
from googlecloudsdk.third_party.apitools.base import py as apitools_base


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
    except apitools_base.HttpError as error:
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
