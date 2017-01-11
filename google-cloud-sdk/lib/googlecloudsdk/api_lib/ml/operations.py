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
"""Utilities for dealing with long-running operations (simple uri)."""

# TODO(b/30137432): Remove this and use api_lib.app.api.operations instead.

from apitools.base.py import encoding

from googlecloudsdk.api_lib.app.api import requests
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import resources
from googlecloudsdk.core.util import retry


class OperationError(exceptions.Error):
  pass


class OperationTimeoutError(exceptions.Error):
  pass


def WaitForOperation(operation_service, operation, registry=None):
  """Wait until the operation is complete or times out.

  Args:
    operation_service: The apitools service type for operations
    operation: The operation resource to wait on
    registry: A resource registry to use for operation get requests.
  Returns:
    The operation resource when it has completed
  Raises:
    OperationTimeoutError: when the operation polling times out
    OperationError: when the operation completed with an error
  """
  if operation.done:
    return operation
  if not registry:
    registry = resources.REGISTRY
  ref = registry.Parse(
      operation.name,
      collection='ml.projects.operations')
  request = (operation_service.client
             .MESSAGES_MODULE.MlProjectsOperationsGetRequest(
                 projectsId=ref.projectsId, operationsId=ref.operationsId))
  try:
    operation = retry.Retryer(max_wait_ms=60 * 60 * 1000).RetryOnResult(
        operation_service.Get,
        args=(request,),
        should_retry_if=lambda op, _: not op.done,
        sleep_ms=5000)
    if operation.error:
      raise OperationError(
          requests.ExtractErrorMessage(
              encoding.MessageToPyValue(operation.error)))
    return operation
  except retry.WaitException:
    raise OperationTimeoutError(
        'Operation [{0}] timed out. This operation may still be underway.'
        .format(operation.name))
