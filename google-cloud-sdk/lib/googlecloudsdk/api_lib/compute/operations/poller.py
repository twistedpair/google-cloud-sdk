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
"""Constructs to poll compute operations."""

from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import resources


class Error(exceptions.Error):
  """Errors raised by this module."""


class OperationErrors(Error):
  """Encapsulates multiple errors reported about single operation."""

  def __init__(self, errors):
    messages = [error.message for error in errors]
    super(OperationErrors, self).__init__(', '.join(messages))


class Poller(waiter.OperationPoller):
  """Compute operations poller."""

  def __init__(self, resource_service, target_ref=None):
    """Initializes poller for compute operations.

    Args:
      resource_service: apitools.base.py.base_api.BaseApiService,
          service representing the target of operation.
      target_ref: Resource, optional reference to the expected target of the
          operation. If not provided operation.targetLink will be used instead.
    """
    self.resource_service = resource_service
    self.client = resource_service.client
    self.messages = self.client.MESSAGES_MODULE
    self.status_enum = self.messages.Operation.StatusValueValuesEnum
    self.target_ref = target_ref

  def IsDone(self, operation):
    """Overrides."""
    if operation.error:
      raise OperationErrors(operation.error.errors)

    return operation.status == self.status_enum.DONE

  def Poll(self, operation_ref):
    """Overrides."""
    if hasattr(operation_ref, 'zone'):
      service = self.client.zoneOperations
    elif hasattr(operation_ref, 'region'):
      service = self.client.regionOperations
    else:
      service = self.client.globalOperations

    return service.Get(service.GetRequestType('Get')(
        **operation_ref.AsDict()))

  def GetResult(self, operation):
    """Overrides."""
    request_type = self.resource_service.GetRequestType('Get')
    target_ref = (self.target_ref
                  or resources.REGISTRY.Parse(operation.targetLink))
    return self.resource_service.Get(
        request_type(**target_ref.AsDict()))

