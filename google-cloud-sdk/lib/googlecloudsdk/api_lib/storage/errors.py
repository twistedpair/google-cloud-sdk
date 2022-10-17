# -*- coding: utf-8 -*- #
# Copyright 2020 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""API interface for interacting with cloud storage providers."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re

from googlecloudsdk.api_lib.util import exceptions as api_exceptions
from googlecloudsdk.api_lib.util import resource
from googlecloudsdk.core import exceptions as core_exceptions

from six.moves import urllib


# For a string /b/bucket-name/o/obj.txt?alt=json, this should match
# b/bucket-name/o/obj.txt
OBJECT_RESOURCE_PATH_PATTERN = re.compile(
    r'b/(?P<bucket>.*)/o/(?P<object>.*?)(\?|$)')


class CloudApiError(core_exceptions.Error):
  pass


class RetryableApiError(CloudApiError):
  """Error raised to indicate a transient network error."""
  pass


class GcsApiError(CloudApiError, api_exceptions.HttpException):
  pass


class NotFoundError(CloudApiError):
  """Error raised when the requested resource does not exist.

  Both GCS and S3 APIs should raise this error if a resource
  does not exist so that the caller can handle the error in an API agnostic
  manner.
  """
  pass


class ResumableUploadAbortError(CloudApiError):
  """Raised when a resumable upload needs to be restarted."""
  pass


class GcsNotFoundError(GcsApiError, NotFoundError):
  """Error raised when the requested GCS resource does not exist.

  Implements custom formatting to avoid messy default.
  """

  def __init__(self, error, *args, **kwargs):
    del args, kwargs  # Unused.
    super(GcsNotFoundError, self).__init__(
        # status_code should be 404, but it's better to rely on the code
        # present in the error message, just in case this class is used
        # incorrectly for a different error.
        error, error_format='gs://{instance_name} not found: {status_code}.')

    if not error.url:
      return

    # Parsing 'instance_name' here because it is not parsed correctly
    # by gcloud's exceptions.py module. See b/225168232.
    _, _, resource_path = resource.SplitDefaultEndpointUrl(error.url)
    # For an object, resource_path will be of the form b/bucket/o/object
    match = OBJECT_RESOURCE_PATH_PATTERN.search(resource_path)
    if match:
      params = urllib.parse.parse_qs(resource_path)
      if 'generation' in params:
        generation_string = '#' + params['generation'][0]
      else:
        # Ideally, a generation is always present for an object, but this is
        # just a safeguard against unexpected formats.
        generation_string = ''
      # Overwrite the instance_name field if it is a GCS object.
      self.payload.instance_name = '{}/{}{}'.format(
          match.group('bucket'), match.group('object'), generation_string)


class S3ErrorPayload(api_exceptions.FormattableErrorPayload):
  """Allows using format strings to create strings from botocore ClientErrors.

  Format strings of the form '{field_name}' will be populated from class
  attributes. Strings of the form '{.field_name}' will be populated from the
  self.content JSON dump. See api_lib.util.HttpErrorPayload for more detail and
  sample usage.

  Attributes:
    content (dict): The dumped JSON content.
    message (str): The human readable error message.
    status_code (int): The HTTP status code number.
    status_description (str): The status_code description.
    status_message (str): Context specific status message.
  """

  def __init__(self, client_error):
    """Initializes an S3ErrorPayload instance.

    Args:
      client_error (Union[botocore.exceptions.ClientError, str]): The error
        thrown by botocore, or a string that will be displayed as the error
        message.
    """
    super(S3ErrorPayload, self).__init__(client_error)
    # TODO(b/170215786): Remove botocore_error_string attribute when S3 api
    # tests no longer expect the botocore error format.
    self.botocore_error_string = str(client_error)
    if hasattr(client_error, 'response'):
      self.content = client_error.response
      if 'ResponseMetadata' in client_error.response:
        self.status_code = client_error.response['ResponseMetadata'].get(
            'HttpStatusCode', 0)
      if 'Error' in client_error.response:
        error = client_error.response['Error']
        self.status_description = error.get('Code', '')
        self.status_message = error.get('Message', '')
      self.message = self._MakeGenericMessage()


class S3ApiError(CloudApiError, api_exceptions.HttpException):
  """Translates a botocore ClientError and allows formatting.

  Attributes:
    error: The original ClientError.
    error_format: An S3ErrorPayload format string.
    payload: The S3ErrorPayload object.
  """

  # TODO(b/170215786): Set error_format=None when S3 api tests no longer expect
  # the botocore error format.
  def __init__(self, error, error_format='{botocore_error_string}'):
    super(S3ApiError, self).__init__(
        error, error_format=error_format, payload_class=S3ErrorPayload)


def translate_error(error, translation_list, format_str=None):
  """Translates error or returns original error if no matches.

  Note, an error will be translated if it is a child class of a value in
  translation_list. Also, translations earlier in the list take priority.

  Args:
    error (Exception): Error to translate.
    translation_list (list): List of (Exception, Exception) tuples. Translates
      errors that are instances of first error type to second. If there is a
      hierarchy, error types earlier in list are translated first.
    format_str (str|None): An api_lib.util.exceptions.FormattableErrorPayload
      format string. Note that any properties that are accessed here are on the
      FormattableErrorPayload object, not the object returned from the server.

  Returns:
    Error (Exception). Translated if match. Else, original error.
  """
  for untranslated_error, translated_error in translation_list:
    if isinstance(error, untranslated_error):
      return translated_error(error, format_str)
  return error


def catch_error_raise_cloud_api_error(translation_list, format_str=None):
  """Decorator catches an error and raises CloudApiError with a custom message.

  Args:
    translation_list (list): List of (Exception, Exception) tuples.
      Translates errors that are instances of first error type to second. If
      there is a hierarchy, error types earlier in list are translated first.
    format_str (str|None): An api_lib.util.exceptions.FormattableErrorPayload
      format string. Note that any properties that are accessed here are on the
      FormattableErrorPayload object, not the object returned from the server.

  Returns:
    A decorator that catches errors and raises a CloudApiError with a
      customizable error message.

  Example:
    @catch_error_raise_cloud_api_error(
        [(apitools_exceptions.HttpError, GcsApiError)],
        'Error [{status_code}]')
    def some_func_that_might_throw_an_error():
  """
  def translate_api_error_decorator(function):
    # Need to define a secondary wrapper to get an argument to the outer
    # decorator.
    def wrapper(*args, **kwargs):
      try:
        return function(*args, **kwargs)
      # pylint:disable=broad-except
      except Exception as e:
        # pylint:enable=broad-except
        core_exceptions.reraise(
            translate_error(e, translation_list, format_str))

    return wrapper

  return translate_api_error_decorator
