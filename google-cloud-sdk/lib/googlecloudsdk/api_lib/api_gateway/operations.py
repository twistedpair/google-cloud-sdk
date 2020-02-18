# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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

"""Client for interaction with Operations CRUD on API Gateway API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.api_gateway import base
from googlecloudsdk.command_lib.api_gateway import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import resources
from googlecloudsdk.core.util import retry


class OperationsClient(base.BaseClient):
  """Client for operation objects on Cloud API Gateway API."""

  def Get(self, operation_ref):
    """Get an operation object.

    Args:
      operation_ref: The message to process (expected to be of type Operation)

    Returns:
      The Operation object.
    """
    request = self.messages.ApigatewayProjectsLocationsOperationsGetRequest(
        name=operation_ref.RelativeName())

    return self.client.projects_locations_operations.Get(request)

  def CheckResult(self, operation_ref):
    """Checks to see if a result object is done.

    Args:
      operation_ref: The message to process (expected to be of type Operation)

    Returns:
      Operation | None
    """
    res = self.Get(operation_ref)

    if res.done:
      return res
    else:
      return None

  def GetOperationResult(self, operation, is_async=False):
    """Validate and process Operation result message for user display.

    This method checks to make sure the result is of type Operation and
    converts the StartTime field from a UTC timestamp to a local datetime
    string.

    Args:
      operation: The message to process (expected to be of type Operation)'
      is_async: If False, the method will block until the operation completes.

    Raises:
      OperationErrorException: When result is an error

    Returns:
      The Operation object.
    """

    if not isinstance(operation, self.messages.ApigatewayOperation):
      raise TypeError('Result must be of type {}'.format(
          self.messages.ApigatewayOperation))

    # If async operation, simply log and return the result on passed in object
    if is_async:
      log.status.Print(
          'Asynchronous operation is in progress. Use the following command to '
          'wait for its completion:\n'
          'gcloud api-gateway operations describe {}\n'.format(operation.name))
      return operation

    # TODO(b/144367107): UImprove output for tracking in progress operations.
    log.status.Print(
        'Waiting for async operation {} to complete...'
        .format(operation.name))

    operation_ref = resources.REGISTRY.Parse(
        operation.name,
        collection='apigateway.projects.locations.operations')
    result = self.WaitForOperationResult(operation_ref)

    # Check for an error in the operation result
    if result.error is not None:
      raise exceptions.OperationErrorException(
          'Operation with ID {} resulted in a failure.'.format(
              operation_ref.Name()))

    return result.response

  def WaitForOperationResult(self, operation_ref):
    """Waits for an operation to complete.

    Args:
      operation_ref: A reference to the operation on which to wait.

    Raises:
      TimeoutError: if the operation does not complete in time.

    Returns:
      The Operation object, if successful. Raises an exception on failure.
    """

    # Wait for no more than 30 minutes while retrying the Operation retrieval
    try:
      retryer = retry.Retryer(exponential_sleep_multiplier=1.1,
                              wait_ceiling_ms=10000,
                              max_wait_ms=30*60*1000)
      result = retryer.RetryOnResult(self.CheckResult,
                                     [operation_ref],
                                     should_retry_if=None,
                                     sleep_ms=1500)
    except retry.MaxRetrialsException:
      raise exceptions.TimeoutError('Timed out while waiting for '
                                    'operation {}. Note that the operation '
                                    'is still pending.'.format(
                                        operation_ref.Name()))

    return result
