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

from googlecloudsdk.api_lib.service_registry import constants
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core.console import progress_tracker


class ServiceRegistryError(exceptions.ToolException):
  """Exception for Service Registry errors."""


class ServiceRegistryClient(object):
  """Supports write operations with asynchronous call handling."""

  OPERATION_TIMEOUT = 10 * 60  # 10 mins

  def __init__(self, client, resources):
    self.client = client
    self.resources = resources

  def call_service_registry(self, call, request, async, log_resource_op):
    """Calls Service Registry, managing asynchronous or otherwise behavior.

    Args:
      call: The function for calling Service Registry.
      request: The request to pass call.
      async: False if this call should poll for the Operation's success.
      log_resource_op: One of log.CreatedResource, log.DeletedResource,
        log.RestoredResource, log.Updatedresource.

    Returns:
      If async=True, returns Operation to poll.
      Else, returns {'name': endpoint_name}.

    Raises:
      HttpException: An http error response was received while executing api
          request.
      ToolException: Call encountered an error.
    """
    result = call(request)
    if isinstance(request.endpoint, basestring):
      endpoint_name = request.endpoint
    else:
      endpoint_name = request.endpoint.name
    if not async:
      operation_ref = self.resources.Parse(
          result.name, collection=constants.OPERATIONS_COLLECTION)
      self.wait_for_operation(operation_ref, result.operationType)
      result = {'name': endpoint_name}
    log_resource_op(endpoint_name, kind='endpoint', async=async)
    return result

  def wait_for_operation(self, operation_ref, operation_description=None):
    """Wait for an operation to complete.

    Polls the operation requested approximately every second, showing a
    progress indicator. Returns when the operation has completed.

    Args:
      operation_ref: A reference to an operation resource.
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
        operation_ref.Name()))
    request = self.client.MESSAGES_MODULE.ServiceregistryOperationsGetRequest(
        project=operation_ref.project, operation=operation_ref.operation)
    with progress_tracker.ProgressTracker(message, autotick=False) as ticker:
      while ticks < self.OPERATION_TIMEOUT:
        operation = self.client.operations.Get(request)
        # Operation status is one of PENDING, RUNNING, DONE
        if operation.status == 'DONE':
          if operation.error:
            raise ServiceRegistryError(
                'Error in Operation [{0}]: {1}'.format(
                    operation_ref.Name(), str(operation.error)))
          else:  # Operation succeeded
            return

        ticks += tick_increment
        ticker.Tick()
        time.sleep(tick_increment)

      # Timeout exceeded
      raise ServiceRegistryError(
          'Wait for Operation [' + operation_ref.Name() + '] exceeded timeout.')
