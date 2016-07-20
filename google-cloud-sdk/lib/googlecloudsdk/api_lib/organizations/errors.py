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
"""Organization API specific error handling exceptions and wrappers."""

import functools
import sys

from apitools.base.py import exceptions as api_exceptions

from googlecloudsdk.api_lib.util import http_error_handler
from googlecloudsdk.calliope import exceptions as calliope_exceptions


def HandleHttpError(func):
  """Decorator that catches HttpError and raises corresponding error."""
  return http_error_handler.HandleHttpErrors(HandleKnownHttpError(func))


def HandleKnownHttpError(func):
  """Decorator that catches specific HttpErrors and raises friendlier errors."""

  @functools.wraps(func)
  def Wrapped(*args, **kwargs):
    try:
      return func(*args, **kwargs)
    except api_exceptions.HttpError as error:
      maybe_known_error = GetError(error)
      if not maybe_known_error:
        raise
      # GetError returns either a tuple or None, the above check ensures it
      # must be a tuple by this point.
      # pylint: disable=unpacking-non-sequence
      error_class, error_args = maybe_known_error
      raise error_class, error_args, sys.exc_info()[2]

  return Wrapped


def GetError(error):
  """Attempts to return a more specific error from an HttpError.

  Args:
    error: HttpError resulting from unsuccessful call to API.

  Returns:
    Either an error class with error arguments tuple for use in a
    "raise class, args, traceback" statement or None if the error code does not
    correspond to a well known error.
  """
  # This will parse organization ID out of error url.
  #   url: .../v1beta1/organizations/BAD_ID?someParam=true&someOtherParam=false
  #   parsed_id: BAD_ID
  org_id = error.url.split('/')[-1].split('?')[0]
  if error.status_code == 403:
    return (OrganizationAccessError, (org_id,))
  elif error.status_code == 404:
    return (OrganizationNotFoundError, (org_id,))
  else:
    return None


class OrganizationNotFoundError(calliope_exceptions.ToolException):
  """The specified Organization does not exist."""

  def __init__(self, org_id):
    message = (
        'Organization [%s] could not be found.\n'
        'To see available organizations, run\n'
        '$ gcloud organizations list' % org_id)
    super(OrganizationNotFoundError, self).__init__(message)


class OrganizationAccessError(calliope_exceptions.ToolException):
  """User does not have permission to access the Organization."""

  def __init__(self, org_id):
    message = (
        'You do not have permission to access organization [%s].' % org_id)
    super(OrganizationAccessError, self).__init__(message)
