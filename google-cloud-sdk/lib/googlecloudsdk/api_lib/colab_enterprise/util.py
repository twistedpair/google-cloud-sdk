# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""A library that is used to support trace commands."""

from apitools.base.py import encoding
from googlecloudsdk.api_lib.util import apis as core_apis
from googlecloudsdk.core import log


def ApiVersionSelector(release_track):
  """Returns the correct API version.

  Args:
    release_track: base.ReleaseTrack object
  """
  return 'v1' if release_track == 'GA' else 'v1beta1'


def GetClient(release_track):
  """Returns the client for the trace API."""
  return core_apis.GetClientInstance(
      'aiplatform', ApiVersionSelector(release_track)
  )


def GetMessages(release_track):
  """Returns the messages for the trace API."""
  return core_apis.GetMessagesModule(
      'aiplatform', ApiVersionSelector(release_track)
  )


def GetAsyncConfig(args):
  """Returns whether the user specified the async flag."""
  return args.async_


def WaitForOpMaybe(
    operations_client,
    op,
    op_ref,
    log_method,
    kind,
    asynchronous=False,
    message=None,
    resource=None,
):
  """Waits for an operation if asynchronous flag is off.

  Args:
    operations_client: api_lib.ai.operations.OperationsClient, the client via
      which to poll.
    op: Cloud AI Platform operation, the operation to poll.
    op_ref: The operation reference to the operation resource. It's the result
      by calling resources.REGISTRY.Parse
    log_method: Logging method used for operation.
    kind: str, the resource kind (eg runtime template), which will be passed to
      logging function.
    asynchronous: bool, whether to wait for the operation or return immediately
    message: str, the message to display while waiting for the operation.
    resource: str, name of the resource the operation is acting on

  Returns:
    The result of the operation if asynchronous is true, or the Operation
      message otherwise.
  """
  logging_function = {
      'create': log.CreatedResource,
      'delete': log.DeletedResource,
      'update': log.UpdatedResource,
  }
  if asynchronous:
    logging_function[log_method](resource=op.name, kind=kind, is_async=True)
    return op
  # Using AIPlatform API lib to wait since the poller in gcloud sdk operations
  # lib doesn't support simple_uri.
  response_msg = operations_client.WaitForOperation(
      op, op_ref, message=message
  ).response
  if response_msg is not None:
    response = encoding.MessageToPyValue(response_msg)
    if 'name' in response:
      resource = response['name']
  logging_function[log_method](
      resource=resource, kind=kind, is_async=False
  )
  return response_msg
