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

"""Tools supporting write commands."""

import time

from googlecloudsdk.api_lib.util import http_error_handler
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io


class ServiceRegistryError(exceptions.ToolException):
  """Exception for Service Registry errors."""


class ServiceRegistryClient(object):
  """Supports write operations with asynchronous call handling."""

  OPERATION_TIMEOUT = 10 * 60  # 10 mins

  def __init__(self, client, messages, project):
    self.client = client
    self.messages = messages
    self.project = project

  @http_error_handler.HandleHttpErrors
  def call_service_registry(self, call, request, async, success_message):
    """Calls Service Registry, managing asynchronous or otherwise behavior.

    Args:
      call: The function for calling Service Registry.
      request: The request to pass call.
      async: False if this call should poll for the Operation's success.
      success_message: A message to print on success of Operation.

    Returns:
      If async=True, returns Operation to poll.
      Else, returns boolean indicating whether call succeeded.

    Raises:
      HttpException: An http error response was received while executing api
          request.
      ToolException: Call encountered an error.
    """
    operation = call(request)
    if async:
      log.Print('Operation {0} is running...'.format(operation.name))
      return operation
    else:
      operation_name = operation.name
      self.wait_for_operation(operation_name,
                              operation.operationType)
      log.status.Print(success_message)

  @http_error_handler.HandleHttpErrors
  def wait_for_operation(
      self, operation_name, operation_description=None):
    """Wait for an operation to complete.

    Polls the operation requested approximately every second, showing a
    progress indicator. Returns when the operation has completed.

    Args:
      operation_name: The name of the operation to wait on, as returned by
          operations.list.
      operation_description: A short description of the operation to wait on,
          such as 'create' or 'delete'. Will be displayed to the user.

    Raises:
        HttpException: A http error response was received while executing api
            request. Will be raised if the operation cannot be found.
        ServiceRegistryError: The operation finished with error(s) or exceeded
            the timeout without completing.
    """
    tick_increment = 1  # every seconds
    ticks = 0
    message = ('Waiting for {0}[{1}]'.format(
        operation_description + ' ' if operation_description else '',
        operation_name))
    with console_io.ProgressTracker(message, autotick=False) as ticker:
      while ticks < self.OPERATION_TIMEOUT:
        operation = self.client.operations.Get(
            self.messages.ServiceregistryOperationsGetRequest(
                project=self.project,
                operation=operation_name,
            )
        )
        # Operation status is one of PENDING, RUNNING, DONE
        if operation.status == 'DONE':
          if operation.error:
            raise ServiceRegistryError(
                'Error in Operation [{0}]: {1}'.format(
                    operation_name, str(operation.error)))
          else:  # Operation succeeded
            return

        ticks += tick_increment
        ticker.Tick()
        time.sleep(tick_increment)

      # Timeout exceeded
      raise ServiceRegistryError(
          'Wait for Operation [' + operation_name + '] exceeded timeout.')
