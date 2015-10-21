# Copyright 2015 Google Inc. All Rights Reserved.

"""Common utility functions for sql errors and exceptions."""

import json
import sys

from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.third_party.apitools.base import py as apitools_base


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
    except apitools_base.HttpError as error:
      msg = GetErrorMessage(error)
      unused_type, unused_value, traceback = sys.exc_info()
      raise calliope_exceptions.HttpException, msg, traceback
  return Func
