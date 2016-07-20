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

"""Common helper methods for Service Management commands."""

import json
import re

from apitools.base.py import encoding
from apitools.base.py import exceptions as apitools_exceptions

from dateutil import parser
from dateutil import tz

from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import apis
from googlecloudsdk.core import log
from googlecloudsdk.core.resource import resource_printer
from googlecloudsdk.core.util import retry

import yaml


EMAIL_REGEX = re.compile(r'^.+@([^.@][^@]+)$')
OP_BASE_CMD = 'gcloud alpha service-management operations '
OP_DESCRIBE_CMD = OP_BASE_CMD + 'describe {0}'
OP_WAIT_CMD = OP_BASE_CMD + 'wait {0}'


def GetMessagesModule():
  return apis.GetMessagesModule('servicemanagement', 'v1')


def GetClientInstance():
  return apis.GetClientInstance('servicemanagement', 'v1')


def GetIamMessagesModule():
  return apis.GetMessagesModule('iam', 'v1')


def GetEndpointsServiceName():
  return 'endpoints.googleapis.com'


def GetServiceManagementServiceName():
  return 'servicemanagement.googleapis.com'


def GetError(error, verbose=False):
  """Returns a ready-to-print string representation from the http response.

  Args:
    error: A string representing the raw json of the Http error response.
    verbose: Whether or not to print verbose messages [default false]

  Returns:
    A ready-to-print string representation of the error.
  """
  data = json.loads(error.content)
  if verbose:
    PrettyPrint(data)
  code = data['error']['code']
  message = data['error']['message']
  return 'ResponseError: code={0}, message={1}'.format(code, message)


def PrettyPrint(resource, print_format='json'):
  """Prints the given resource."""
  resource_printer.Print(
      resources=[resource],
      print_format=print_format,
      out=log.out)


def ConvertUTCDateTimeStringToLocalTimeString(utc_string):
  """Returns a string representation of the given UTC string in local time.

  Args:
    utc_string: The string representation of the UTC datetime.

  Returns:
    A string representing the input time in local time. The format will follow
    '%Y-%m-%d %H:%M:%S %Z'.
  """
  dt_parser = parser.parser()
  try:
    utc_dt = dt_parser.parse(utc_string)
  except ValueError:
    log.warn('Failed to parse UTC string %s', utc_string)
    return utc_string
  except OverflowError:
    log.warn('Parsed UTC date exceeds largest valid C integer on this system')
    return utc_string
  loc_dt = utc_dt.astimezone(tz.tzlocal())
  fmt = '%Y-%m-%d %H:%M:%S %Z'
  return loc_dt.strftime(fmt)


def GetByteStringFromFingerprint(fingerprint):
  """Helper function to create a byte string from a SHA fingerprint.

  Args:
    fingerprint: The fingerprint to transform in the form of
                 "12:34:56:78:90:...:EF".

  Returns:
    The fingerprint converted to a byte string (excluding the colons).
  """
  if not ValidateFingerprint(fingerprint):
    raise exceptions.ToolException('Invalid fingerprint')
  byte_tokens = fingerprint.split(':')
  return str(bytearray([int(b, 16) for b in byte_tokens]))


_FINGERPRINT_RE = re.compile(
    r'^([a-f0-9][a-f0-9]:){19}[a-f0-9][a-f0-9]$', re.IGNORECASE)


def ValidateFingerprint(fingerprint):
  return re.match(_FINGERPRINT_RE, fingerprint) is not None


def ValidateEmailString(email):
  """Returns true if the input is a valid email string.

  This method uses a somewhat rudimentary regular expression to determine
  input validity, but it should suffice for basic sanity checking.

  It also verifies that the email string is no longer than 254 characters,
  since that is the specified maximum length.

  Args:
    email: The email string to validate

  Returns:
    A bool -- True if the input is valid, False otherwise
  """
  return EMAIL_REGEX.match(email or '') is not None and len(email) <= 254


def ProcessOperationResult(result, async=False):
  """Validate and process Operation outcome for user display.

  Args:
    result: The message to process (expected to be of type Operation)'
    async: If False, the method will block until the operation completes.
  """
  op = GetProcessedOperationResult(result, async)
  cmd = OP_DESCRIBE_CMD.format(op.get('name'))
  if async:
    cmd = OP_WAIT_CMD.format(op.get('name'))
    log.status.Print('Asynchronous operation is in progress... '
                     'Use the following command to wait for its '
                     'completion:\n {0}'.format(cmd))
  else:
    cmd = OP_DESCRIBE_CMD.format(op.get('name'))
    log.status.Print('Operation finished successfully. '
                     'The following command can describe '
                     'the Operation details:\n {0}'.format(cmd))


def GetProcessedOperationResult(result, async=False):
  """Validate and process Operation result message for user display.

  This method checks to make sure the result is of type Operation and
  converts the StartTime field from a UTC timestamp to a local datetime
  string.

  Args:
    result: The message to process (expected to be of type Operation)'
    async: If False, the method will block until the operation completes.

  Returns:
    The processed message in Python dict form
  """
  if not result:
    return

  messages = GetMessagesModule()

  RaiseIfResultNotTypeOf(result, messages.Operation)

  result_dict = encoding.MessageToDict(result)

  if not async:
    op_name = result_dict['name']
    log.status.Print(
        'Waiting for async operation {0} to complete...'.format(op_name))
    result_dict = encoding.MessageToDict(WaitForOperation(
        op_name, apis.GetClientInstance('servicemanagement', 'v1')))

  # Convert metadata startTime to local time
  if 'metadata' in result_dict and 'startTime' in result_dict['metadata']:
    result_dict['metadata']['startTime'] = (
        ConvertUTCDateTimeStringToLocalTimeString(
            result_dict['metadata']['startTime']))

  return result_dict


def RaiseIfResultNotTypeOf(test_object, expected_type, nonetype_ok=False):
  if nonetype_ok and test_object is None:
    return
  if not isinstance(test_object, expected_type):
    raise TypeError('result must be of type %s' % expected_type)


def GetCallerViews():
  messages = GetMessagesModule()
  get_request = messages.ServicemanagementServicesProjectSettingsGetRequest
  return {
      'CONSUMER': get_request.ViewValueValuesEnum.CONSUMER_VIEW,
      'PRODUCER': get_request.ViewValueValuesEnum.PRODUCER_VIEW,
      'ALL': get_request.ViewValueValuesEnum.ALL,
  }


OPTIONAL_PREFIX_TO_STRIP = 'operations/'


def WaitForOperation(op_name, client):
  """Waits for an operation to complete.

  Args:
    op_name: The name of the operation on which to wait.
    client: The client object that contains the GetOperation request object.

  Raises:
    ToolException: if the operation fails or does not complete in time.

  Returns:
    The Operation object, if successful. Raises an exception on failure.
  """
  WaitForOperation.operation_response = None

  messages = GetMessagesModule()

  def _CheckOperation(op_name):  # pylint: disable=missing-docstring
    # If a user includes the leading "operations/", just strip it off
    if op_name.startswith(OPTIONAL_PREFIX_TO_STRIP):
      op_name = op_name[len(OPTIONAL_PREFIX_TO_STRIP):]

    request = messages.ServicemanagementOperationsGetRequest(
        operationsId=op_name,
    )

    try:
      result = client.operations.Get(request)
    except apitools_exceptions.HttpError as error:
      raise exceptions.HttpException(GetError(error))

    if result.done:
      WaitForOperation.operation_response = result
      return True
    else:
      return False

  # Wait for no more than 30 minutes while retrying the Operation retrieval
  try:
    retry.Retryer(exponential_sleep_multiplier=1.1, wait_ceiling_ms=10000,
                  max_wait_ms=30*60*1000).RetryOnResult(
                      _CheckOperation, [op_name], should_retry_if=False,
                      sleep_ms=1500)
  except retry.MaxRetrialsException:
    raise exceptions.ToolException('Timed out while waiting for '
                                   'operation %s. Note that the operation '
                                   'is still pending.' % op_name)

  # Check to see if the operation resulted in an error
  if WaitForOperation.operation_response.error is not None:
    raise exceptions.ToolException(
        'The operation with ID {0} resulted in a failure.'.format(op_name))

  # If we've gotten this far, the operation completed successfully,
  # so return the Operation object
  return WaitForOperation.operation_response


def LoadJsonOrYaml(input_string):
  """Tries to load input string as JSON first, then YAML if that fails.

  Args:
    input_string: The string to convert to a dictionary

  Returns:
    A dictionary of the resulting decoding, or None if neither format could be
    detected.
  """
  def TryJson():
    try:
      return json.loads(input_string)
    except ValueError:
      log.info('No JSON detected in service config. Trying YAML...')

  def TryYaml():
    try:
      return yaml.load(input_string)
    except yaml.YAMLError as e:
      if hasattr(e, 'problem_mark'):
        mark = e.problem_mark
        log.error('Service config YAML had an error at position (%s:%s)'
                  % (mark.line+1, mark.column+1))

  # First, try to decode JSON. If that fails, try to decode YAML.
  return TryJson() or TryYaml()
