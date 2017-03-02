# Copyright 2014 Google Inc. All Rights Reserved.
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

"""A shared library to support implementation of Firebase Test Lab commands."""

import json

from apitools.base.py import exceptions as apitools_exceptions

from googlecloudsdk.api_lib.test import exceptions
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties


def GetError(error):
  """Returns a ready-to-print string representation from the http response.

  Args:
    error: the Http error response, whose content is a JSON-format string for
      most cases (e.g. invalid test dimension), but can be just a string other
      times (e.g. invalid URI for CLOUDSDK_TEST_ENDPOINT).

  Returns:
    A ready-to-print string representation of the error.
  """
  try:
    data = json.loads(error.content)
  except ValueError:  # message is not JSON
    return error.content

  code = data['error']['code']
  message = data['error']['message']
  return 'ResponseError {0}: {1}'.format(code, message)


def GetErrorCodeAndMessage(error):
  """Returns the individual error code and message from a JSON http response.

  Prefer using GetError(error) unless you need to examine the error code and
  take specific action on it.

  Args:
    error: the Http error response, whose content is a JSON-format string.

  Returns:
    (code, msg) A tuple holding the error code and error message string.

  Raises:
    ValueError: if the error is not in JSON format.
  """
  data = json.loads(error.content)
  return data['error']['code'], data['error']['message']


def GetProject():
  """Get the user's project id from the core project properties.

  Returns:
    The id of the GCE project to use while running the test.

  Raises:
    MissingProjectError: if the user did not specify a project id via the
      --project flag or via running "gcloud config set project PROJECT_ID".
  """
  project = properties.VALUES.core.project.Get()
  if not project:
    raise exceptions.MissingProjectError(
        'No project specified. Please add --project PROJECT_ID to the command'
        ' line or first run\n  $ gcloud config set project PROJECT_ID')
  return project


def GetAndroidCatalog(context):
  """Gets the Android catalog from the TestEnvironmentDiscoveryService.

  Args:
    context: {str:object}, The current context, which is a set of key-value
      pairs that can be used for common initialization among commands.

  Returns:
    The android catalog.

  Raises:
    calliope_exceptions.HttpException: If it could not connect to the service.
  """
  env_type = (context['testing_messages']
              .TestingTestEnvironmentCatalogGetRequest
              .EnvironmentTypeValueValuesEnum.ANDROID)
  return _GetCatalog(context, env_type).androidDeviceCatalog


def _GetCatalog(context, environment_type):
  """Gets a test environment catalog from the TestEnvironmentDiscoveryService.

  Args:
    context: {str:object}, The current context, which is a set of key-value
      pairs that can be used for common initialization among commands.
    environment_type: Value from the EnvironmentType enum.

  Returns:
    The test environment catalog.

  Raises:
    calliope_exceptions.HttpException: If it could not connect to the service.
  """
  client = context['testing_client']
  messages = context['testing_messages']

  request = messages.TestingTestEnvironmentCatalogGetRequest()
  request.environmentType = environment_type
  try:
    return client.testEnvironmentCatalog.Get(request)
  except apitools_exceptions.HttpError as error:
    raise calliope_exceptions.HttpException(
        'Unable to access the test environment catalog: ' + GetError(error))
  except:
    # Give the user some explanation in case we get a vague/unexpected error,
    # such as a socket.error from httplib2.
    log.error('Unable to access the test environment catalog.')
    raise  # Re-raise the error in case Calliope can do something with it.
