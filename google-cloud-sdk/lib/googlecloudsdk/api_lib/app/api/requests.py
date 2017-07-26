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

"""Utilities for making requests using a given client and handling errors.
"""

import io

from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.app import exceptions as api_lib_exceptions
from googlecloudsdk.api_lib.util import exceptions as http_exception
from googlecloudsdk.core import log
from googlecloudsdk.core.resource import resource_printer


ERROR_FORMAT_STRING = ('Error Response:{status_code? [{?}]}'
                       '{status_message? {?}}{url?\n{?}}'
                       '{details?\n\nDetails:\n{?}}')


def ExtractErrorMessage(error_details):
  """Extracts error details from an apitools_exceptions.HttpError.

  Args:
    error_details: a python dictionary returned from decoding an error that
        was serialized to json.

  Returns:
    Multiline string containing a detailed error message suitable to show to a
    user.
  """
  error_message = io.BytesIO()
  error_message.write('Error Response: [{code}] {message}'.format(
      code=error_details.get('code', 'UNKNOWN'),  # error_details.code is an int
      message=error_details.get('message', u'').encode('utf-8')))

  if 'url' in error_details:
    error_message.write('\n' + error_details['url'].encode('utf-8'))

  if 'details' in error_details:
    error_message.write('\n\nDetails: ')
    resource_printer.Print(
        resources=[error_details['details']],
        print_format='json',
        out=error_message)
  return error_message.getvalue()


def MakeRequest(service_method, request_message):
  """Makes a request using the given client method and handles HTTP errors."""
  try:
    return service_method(request_message)
  except apitools_exceptions.HttpError as error:
    log.debug(error)
    exc = http_exception.HttpException(error, error_format=ERROR_FORMAT_STRING)
    # Make it easier to switch on certain common error codes.
    err = api_lib_exceptions.STATUS_CODE_TO_ERROR.get(exc.payload.status_code)
    if err:
      raise err
    raise exc
