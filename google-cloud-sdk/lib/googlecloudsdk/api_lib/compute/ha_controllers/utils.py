# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Utilities for HA controllers."""

from googlecloudsdk.api_lib.compute.operations import poller
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import log


def Insert(holder, ha_controller, ha_controller_ref, async_):
  """Inserts an HA Controller."""
  if not async_:
    return _Insert(ha_controller, ha_controller_ref, holder)
  return _ExecuteAsyncOperation(
      _InsertAsync, holder, ha_controller, ha_controller_ref,
      operation_type='creation'
  )


def Patch(holder, ha_controller, ha_controller_ref, async_):
  """Patches an HA Controller."""
  if not async_:
    return _Patch(ha_controller, ha_controller_ref, holder)
  return _ExecuteAsyncOperation(
      _PatchAsync, holder, ha_controller, ha_controller_ref,
      operation_type='update'
  )


def _CreateInsertRequest(client, ha_controller, ha_controller_ref):
  return client.messages.ComputeHaControllersInsertRequest(
      haController=ha_controller,
      project=ha_controller_ref.project,
      region=ha_controller_ref.region,
  )


def _Insert(ha_controller, ha_controller_ref, holder):
  request = _CreateInsertRequest(
      holder.client, ha_controller, ha_controller_ref
  )
  response = holder.client.apitools_client.haControllers.Insert(request)
  operation_ref = holder.resources.Parse(response.selfLink)
  return waiter.WaitFor(
      poller.Poller(holder.client.apitools_client.haControllers),
      operation_ref,
      message=(
          'HA controller creation in progress for [{}]: {}'.format(
              ha_controller.name, operation_ref.SelfLink()
          )
      ),
  )


def _InsertAsync(client, ha_controller, ha_controller_ref, errors_to_collect):
  request = _CreateInsertRequest(client, ha_controller, ha_controller_ref)
  return client.AsyncRequests(
      [(client.apitools_client.haControllers, 'Insert', request)],
      errors_to_collect
  )[0]


def _Patch(ha_controller, ha_controller_ref, holder):
  request = holder.client.messages.ComputeHaControllersPatchRequest(
      haController=ha_controller_ref.Name(),
      haControllerResource=ha_controller,
      project=ha_controller_ref.project,
      region=ha_controller_ref.region,
  )
  response = holder.client.apitools_client.haControllers.Patch(request)
  operation_ref = holder.resources.Parse(response.selfLink)
  return waiter.WaitFor(
      poller.Poller(holder.client.apitools_client.haControllers),
      operation_ref,
      message=(
          'HA controller update in progress for [{}]: {}'.format(
              ha_controller.name, operation_ref.SelfLink()
          )
      ),
  )


def _PatchAsync(client, ha_controller, ha_controller_ref, errors_to_collect):
  request = client.messages.ComputeHaControllersPatchRequest(
      haController=ha_controller_ref.Name(),
      haControllerResource=ha_controller,
      project=ha_controller_ref.project,
      region=ha_controller_ref.region,
  )
  return client.AsyncRequests(
      [(client.apitools_client.haControllers, 'Patch', request)],
      errors_to_collect
  )[0]


def Get(client, ha_controller_ref):
  """Send HA Controller get request."""
  return client.apitools_client.haControllers.Get(
      client.messages.ComputeHaControllersGetRequest(
          **ha_controller_ref.AsDict()
      )
  )


def _HandleAsyncResponse(response, holder, ha_controller_name, operation_type):
  """Handles the response from an asynchronous HA Controller operation."""
  err = getattr(response, 'error', None)
  if err:
    raise core_exceptions.MultiError([poller.OperationErrors(err.errors)])

  operation_ref = holder.resources.Parse(response.selfLink)

  log.status.Print(
      'HA Controller {} in progress for [{}]: {}'.format(
          operation_type, ha_controller_name, operation_ref.SelfLink()
      )
  )
  log.status.Print(
      'Use [gcloud compute operations describe URI] command '
      'to check the status of the operation.'
  )
  return response


def _ExecuteAsyncOperation(
    async_method, holder, ha_controller, ha_controller_ref, operation_type
):
  """Executes an asynchronous HA Controller operation."""
  errors_to_collect = []
  response = async_method(
      holder.client, ha_controller, ha_controller_ref, errors_to_collect
  )
  if errors_to_collect:
    raise core_exceptions.MultiError(errors_to_collect)
  return _HandleAsyncResponse(
      response, holder, ha_controller.name, operation_type
  )
