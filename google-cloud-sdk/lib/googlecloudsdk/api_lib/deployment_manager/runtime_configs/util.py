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

"""Common helper methods for Runtime Config commands."""

import socket
from string import lstrip

from apitools.base.py import encoding

from googlecloudsdk.api_lib.deployment_manager.runtime_configs import exceptions as rtc_exceptions
from googlecloudsdk.calliope import exceptions as sdk_exceptions
from googlecloudsdk.core import apis
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.util import retry

# The important substring from the error message "The read operation
# timed out".
TIMEOUT_ERR_TEXT = 'read operation timed out'

# The maximum number of seconds that a waiter timeout value can be set to.
# TODO(user): figure out proper maximum value
MAX_WAITER_TIMEOUT = 60 * 60 * 12  # 12 hours

# Default number of seconds to sleep between checking waiter status.
DEFAULT_WAITER_SLEEP = 5  # 5 seconds


def ProjectPath(project):
  return '/'.join(['projects', project])


def ConfigPath(project, config):
  return '/'.join([ProjectPath(project), 'configs', config])


def VariablePath(project, config, variable):
  return '/'.join([ConfigPath(project, config), 'variables',
                   lstrip(variable, '/')])


def WaiterPath(project, config, waiter):
  return '/'.join([ConfigPath(project, config), 'waiters', waiter])


def ParseConfigName(config_name):
  """Parse a config name or URL, and return a resource.

  Args:
    config_name: The config name.

  Returns:
    The parsed resource.
  """
  params = {
      'projectsId': Project
  }
  return resources.Parse(config_name,
                         collection='runtimeconfig.projects.configs',
                         params=params)


def _ParseMultipartName(name, args, collection, resource_field):
  """Parse a multi-part name or URL, and return a resource.

  Args:
    name: The resource name or URL.
    args: CLI arguments, possibly containing a config name.
    collection: The resource collection name.
    resource_field: The field within the resulting resource that contains the
        resource name. E.g., "variablesId".

  Returns:
    The parsed resource.
  """
  params = {
      'projectsId': lambda: ParseConfigName(ConfigName(args)).projectsId,
      'configsId': lambda: ParseConfigName(ConfigName(args)).configsId
  }

  # Workaround for resources.Parse's inability to parse names with '/'
  # characters. If the given resource name is not a full http URL,
  # set the resource_field parameter to the name and pass None as the
  # string to parse. This causes Parse to construct a resource using
  # only the provided separate parameters.

  if IsHttpResourceName(name):
    resource_name = name
  else:
    resource_name = None
    params[resource_field] = name

  return resources.Parse(resource_name,
                         collection=collection,
                         params=params)


def ParseVariableName(variable_name, args):
  """Parse a variable name or URL, and return a resource.

  Args:
    variable_name: The variable name.
    args: CLI arguments, possibly containing a config name.

  Returns:
    The parsed resource.
  """
  return _ParseMultipartName(variable_name, args,
                             'runtimeconfig.projects.configs.variables',
                             'variablesId')


def ParseWaiterName(waiter_name, args):
  """Parse a waiter name or URL, and return a resource.

  Args:
    waiter_name: The waiter name.
    args: CLI arguments, possibly containing a config name.

  Returns:
    The parsed resource.
  """
  params = {
      'projectsId': lambda: ParseConfigName(ConfigName(args)).projectsId,
      'configsId': lambda: ParseConfigName(ConfigName(args)).configsId
  }

  return resources.Parse(waiter_name,
                         collection='runtimeconfig.projects.configs.waiters',
                         params=params)


def ConfigName(args, required=True):
  if required and not getattr(args, 'config_name', None):
    raise sdk_exceptions.RequiredArgumentException(
        'config', '--config-name parameter is required.')

  return getattr(args, 'config_name', None)


def Client(timeout=None, num_retries=None):
  client = apis.GetClientInstance('runtimeconfig', 'v1beta1')

  if timeout is not None:
    client.http.timeout = timeout
  if num_retries is not None:
    client.num_retries = num_retries

  return client


def ConfigClient(**kwargs):
  return Client(**kwargs).projects_configs


def VariableClient(**kwargs):
  return Client(**kwargs).projects_configs_variables


def WaiterClient(**kwargs):
  return Client(**kwargs).projects_configs_waiters


def Messages():
  return apis.GetMessagesModule('runtimeconfig', 'v1beta1')


def Project(required=True):
  return properties.VALUES.core.project.Get(required=required)


def IsNotFoundError(error):
  return getattr(error, 'status_code', None) == 404


def IsAlreadyExistsError(error):
  return getattr(error, 'status_code', None) == 409


def IsBadGatewayError(error):
  return getattr(error, 'status_code', None) == 502


def IsDeadlineExceededError(error):
  return getattr(error, 'status_code', None) == 504


def IsHttpResourceName(name):
  name = name.lower()
  return name.startswith('http://') or name.startswith('https://')


def IsSocketTimeout(error):
  # For SSL timeouts, the error does not extend socket.timeout.
  # There doesn't appear to be any way to differentiate an SSL
  # timeout from any other SSL error other than checking the
  # message. :(
  return isinstance(error, socket.timeout) or TIMEOUT_ERR_TEXT in error.message


def WaitForWaiter(waiter_resource, sleep=None, max_wait=None):
  """Wait for a waiter to finish.

  Args:
    waiter_resource: The waiter resource to wait for.
    sleep: The number of seconds to sleep between status checks.
    max_wait: The maximum number of seconds to wait before an error is raised.

  Returns:
    The last retrieved value of the Waiter.

  Raises:
    WaitTimeoutError: If the wait operation takes longer than the maximum wait
        time.
  """
  sleep = sleep if sleep is not None else DEFAULT_WAITER_SLEEP
  max_wait = max_wait if max_wait is not None else MAX_WAITER_TIMEOUT
  waiter_client = WaiterClient()
  retryer = retry.Retryer(max_wait_ms=max_wait * 1000)

  with console_io.ProgressTracker(
      'Waiting for waiter [{0}] to finish'.format(waiter_resource.Name())):
    try:
      result = retryer.RetryOnResult(waiter_client.Get,
                                     args=[waiter_resource.Request()],
                                     sleep_ms=sleep * 1000,
                                     should_retry_if=lambda w, s: not w.done)
    except retry.WaitException:
      raise rtc_exceptions.WaitTimeoutError(
          'Waiter [{0}] did not finish within {1} seconds.'.format(
              waiter_resource.Name(), max_wait))

  if result.error is not None:
    if result.error.message is not None:
      message = 'Waiter [{0}] finished with an error: {1}'.format(
          waiter_resource.Name(), result.error.message)
    else:
      message = 'Waiter [{0}] finished with an error.'.format(
          waiter_resource.Name())
    log.error(message)

  return result


def IsFailedWaiter(waiter):
  """Returns True if the specified waiter has failed."""
  return waiter.error is not None


def _DictWithShortName(message, name_converter):
  """Returns a dict representation of the message with a shortened name value.

  This method does three things:
  1. converts message to a dict.
  2. shortens the value of the name field using name_converter
  3. sets atomicName to the original value of name.

  Args:
    message: A protorpclite message.
    name_converter: A function that takes an atomic name as a parameter and
        returns a shortened name.

  Returns:
    A dict representation of the message with a shortened name field.

  Raises:
    ValueError: If the original message already contains an atomicName field.
  """
  message_dict = encoding.MessageToDict(message)

  # Defend against the unlikely scenario where the original message
  # already has an 'atomicName' field.
  if 'name' in message_dict:
    if 'atomicName' in message_dict:
      raise ValueError('Original message cannot contain an atomicName field.')

    message_dict['atomicName'] = message_dict['name']
    message_dict['name'] = name_converter(message_dict['name'])

  return message_dict


def FormatConfig(message):
  """Returns the config message as a dict with a shortened name."""
  # Example name:
  #   "projects/my-project/configs/my-config"
  # name.split('/')[-1] returns 'my-config'.
  return _DictWithShortName(message, lambda name: name.split('/')[-1])


def FormatVariable(message):
  """Returns the variable message as a dict with a shortened name."""
  # Example name:
  #   "projects/my-project/configs/my-config/variables/my/var"
  # '/'.join(name.split('/')[5:]) returns 'my/var'
  return _DictWithShortName(message, lambda name: '/'.join(name.split('/')[5:]))


def FormatWaiter(message):
  """Returns the waiter message as a dict with a shortened name."""
  # Example name:
  #   "projects/my-project/configs/my-config/waiters/my-waiter"
  # name.split('/')[-1] returns 'my-waiter'
  return _DictWithShortName(message, lambda name: name.split('/')[-1])
