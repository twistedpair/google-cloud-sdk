# Copyright 2015 Google Inc. All Rights Reserved.

"""Utilities for building the dataflow CLI."""

import json

from googlecloudsdk.core import log


def GetErrorMessage(error):
  """Extract the error message from an HTTPError.

  Args:
    error: The error apitools_base.HttpError thrown by the API client.

  Returns:
    A string describing the error.
  """
  try:
    content_obj = json.loads(error.content)
    return content_obj.get('error', {}).get('message', '')
  except ValueError:
    log.err.Print(error.response)
    return 'Unknown error'
