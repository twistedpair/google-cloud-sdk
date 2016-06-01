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
import json
import sys

from googlecloudsdk.core import exceptions
from googlecloudsdk.third_party.apitools.base.py import exceptions


def HandleHttpError(func):
  """Decorator that catches HttpError and raises corresponding error."""

  @functools.wraps(func)
  def CatchHTTPErrorRaiseHTTPException(*args, **kwargs):
    try:
      return func(*args, **kwargs)
    except exceptions.HttpError as error:
      error_class, error_args = GetError(error)
      raise error_class, error_args, sys.exc_info()[2]

  return CatchHTTPErrorRaiseHTTPException


def GetError(error):
  """Returns a more specific error from an HttpError.

  Args:
    error: HttpError resulting from unsuccessful call to API.

  Returns:
    Error class with error arguments tuple for use in a
    "raise class, args, traceback" statement
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
    return (UnknownError, (error,))


class OrganizationNotFoundError(exceptions.Error):
  """The specified Organization does not exist."""

  def __init__(self, org_id):
    message = (
        'Organization [%s] could not be found.\n'
        'To see available organizations, run\n'
        '$ gcloud organizations list' % org_id)
    super(OrganizationNotFoundError, self).__init__(message)


class OrganizationAccessError(exceptions.Error):
  """User does not have permission to access the Organization."""

  def __init__(self, org_id):
    message = (
        'You do not have permission to access organization [%s].' % org_id)
    super(OrganizationAccessError, self).__init__(message)


class UnknownError(exceptions.Error):
  """An unknown error occurred."""

  def __init__(self, error):
    error_content = json.loads(error.content)['error']
    message = '%s %s' % (error_content['code'], error_content['message'])
    super(UnknownError, self).__init__(message)
