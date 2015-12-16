# Copyright 2015 Google Inc. All Rights Reserved.

"""Utilities for making requests using a given client and handling errors.
"""

import cStringIO
import json

from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import resource_printer
from googlecloudsdk.third_party.apitools.base.py import exceptions as apitools_exceptions

import httplib2


def TransformKnownErrors(error):
  """Modify common error responses for friendly presentation to users.

  Currently transforms:

  * API not enabled: instructions on enabling the API

  Args:
    error: dict, parsed JSON error

  Returns:
    error, possibly modified to present better to users
  """
  log.debug(error)

  if (error.get('status') == 'PERMISSION_DENIED' and
      'Project has not enabled the API' in error.get('message', '')):
    url = 'https://console.developers.google.com/'
    try:
      # 'details' is a list of details for the error; with this message, there's
      # only one. 'links' is a list of relevant links; in this message, there's
      # only one.
      url = error['details'][0]['links'][0]['url']
    except (IndexError, KeyError):
      pass
    error['message'] = (
        'You must enable the "App Engine Admin API" in the Developers Console '
        'in order to use this command:\n\n'
        '1. Go to <{0}>.\n'
        '2. Find and enable the "App Engine Admin API" in the '
        '"APIs and Auth > APIs" view.').format(url)

  return error


def ExtractErrorMessage(error_details):
  """Extracts error details from an apitools_exceptions.HttpError."""
  error_message = cStringIO.StringIO()
  error_message.write('Error Response: [{code}] {message}'.format(
      code=error_details.get('code', 'UNKNOWN'),
      message=error_details.get('message', '')))
  if 'url' in error_details:
    error_message.write('\n{url}'.format(url=error_details['url']))

  if error_details.get('details'):
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
    error_json = _ExtractErrorJsonFromHttpError(error)
    error_json = TransformKnownErrors(error_json)
    raise exceptions.HttpException(ExtractErrorMessage(error_json))
  except httplib2.HttpLib2Error as error:
    raise exceptions.HttpException('Response error: %s' % error.message)


def _ExtractErrorJsonFromHttpError(error):
  try:
    return json.loads(error.content)['error']
  except (ValueError, KeyError):
    return {'code': error.response['status'], 'message': error.content,
            'url': error.url}
