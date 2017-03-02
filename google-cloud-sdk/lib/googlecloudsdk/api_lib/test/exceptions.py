# Copyright 2017 Google Inc. All Rights Reserved.
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

"""Exceptions raised by Testing API libs or commands."""

from googlecloudsdk.api_lib.test import exit_code
from googlecloudsdk.core import exceptions as core_exceptions


class TestingError(core_exceptions.Error):
  """Base class for testing failures."""


class MissingProjectError(TestingError):
  """No GCP project was specified for a command."""


class BadMatrixError(TestingError):
  """BadMatrixException is for test matrices that fail prematurely."""


class ModelNotFoundError(TestingError):
  """Failed to find a device model in the test environment catalog."""

  def __init__(self, model_id):
    super(ModelNotFoundError, self).__init__(
        "Could not find model ID '{id}'".format(id=model_id))


class TestExecutionNotFoundError(TestingError):
  """A test execution ID was not found within a test matrix."""

  def __init__(self, execution_id, matrix_id):
    super(TestExecutionNotFoundError, self).__init__(
        'Test execution [{e}] not found in matrix [{m}].'
        .format(e=execution_id, m=matrix_id))


class IncompatibleApiEndpointsError(TestingError):
  """Two or more API endpoint overrides are incompatible with each other."""

  def __init__(self, endpoint1, endpoint2):
    super(IncompatibleApiEndpointsError, self).__init__(
        'Service endpoints [{0}] and [{1}] are not compatible.'
        .format(endpoint1, endpoint2))


class InvalidTestArgError(TestingError):
  """An invalid/unknown test argument was found in an argument file."""

  def __init__(self, arg_name):
    super(InvalidTestArgError, self).__init__(
        '[{0}] is not a valid argument name for: gcloud test run.'
        .format(arg_name))


class TestLabInfrastructureError(TestingError):
  """Encountered a Firebase Test Lab infrastructure error during testing."""

  def __init__(self, error):
    super(TestLabInfrastructureError, self).__init__(
        'Firebase Test Lab infrastructure failure: {0}'.format(error),
        exit_code=exit_code.INFRASTRUCTURE_ERR)


class AllDimensionsIncompatibleError(TestingError):
  """All device dimensions in a test matrix are incompatible."""

  def __init__(self, msg):
    super(AllDimensionsIncompatibleError, self).__init__(
        msg, exit_code=exit_code.UNSUPPORTED_ENV)

