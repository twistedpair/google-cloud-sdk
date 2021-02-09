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
"""CRM operations utilities."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.resource_manager import tags
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import resources


class OperationError(exceptions.Error):
  pass


def WaitForOperation(operation, message, service):
  """Waits for the given google.longrunning.Operation to complete.

  Args:
    operation: The operation to poll.
    message: String to display for default progress_tracker.
    service: The service to get the resource after the long running operation
      completes.

  Raises:
    apitools.base.py.HttpError: if the request returns an HTTP error

  Returns:
    The TagKey or TagValue resource.
  """
  poller = waiter.CloudOperationPoller(service, tags.OperationsService())
  if poller.IsDone(operation):
    # Use the poller to get the result so it prints the same regardless if the
    # Operation is immediately done or not. Currently the poller will raise a
    # KeyError because it assumes a 'name' field  which is not present when
    # the Operation response is of type Empty.
    try:
      return poller.GetResult(operation)
    except KeyError:
      return operation

  operation_ref = resources.REGISTRY.Parse(
      operation.name, collection='cloudresourcemanager.operations')
  return waiter.WaitFor(poller, operation_ref, message)
