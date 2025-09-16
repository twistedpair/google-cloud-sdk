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


def CreateInsertRequest(client, ha_controller, ha_controller_ref):
  return client.messages.ComputeHaControllersInsertRequest(
      haController=ha_controller,
      project=ha_controller_ref.project,
      region=ha_controller_ref.region,
  )


def Insert(ha_controller, ha_controller_ref, holder):
  request = CreateInsertRequest(holder.client, ha_controller, ha_controller_ref)
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


def InsertAsync(client, ha_controller, ha_controller_ref, errors_to_collect):
  request = CreateInsertRequest(client, ha_controller, ha_controller_ref)
  return client.AsyncRequests(
      [(client.apitools_client.haControllers, 'Insert', request)],
      errors_to_collect
  )[0]
