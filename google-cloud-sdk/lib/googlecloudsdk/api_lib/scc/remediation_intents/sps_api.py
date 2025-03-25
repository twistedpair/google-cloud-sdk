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
"""Utility functions to call Security Posture API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import datetime

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base
from googlecloudsdk.core import resources


API_NAME = 'securityposture'
VERSION_MAP = {
    base.ReleaseTrack.ALPHA: 'v1alpha',
    base.ReleaseTrack.GA: 'v1'
}


def GetMessagesModule(release_track=base.ReleaseTrack.ALPHA):
  api_version = VERSION_MAP.get(release_track)
  return apis.GetMessagesModule(API_NAME, api_version)


def GetClientInstance(release_track=base.ReleaseTrack.ALPHA):
  api_version = VERSION_MAP.get(release_track)
  return apis.GetClientInstance(API_NAME, api_version)


def GetOperationsRef(operation_id, release_track=base.ReleaseTrack.ALPHA):
  """Operations to Resource used for `waiter.WaitFor`.

  Args:
    operation_id: The operation ID for which resource reference is required.
    release_track: The release track to use for the API version.

  Returns:
    The resource reference for the operation.
  """
  return resources.REGISTRY.ParseRelativeName(
      operation_id,
      collection='securityposture.organizations.locations.operations',
      api_version=VERSION_MAP.get(release_track),
  )


def WaitForOperation(
    operation_ref,
    message,
    has_result=False,
    release_track=base.ReleaseTrack.ALPHA,
    max_wait=datetime.timedelta(seconds=600),
):
  """Waits for an operation to complete.

  Polls the Security Posture Operations service until the operation completes,
  fails, or max_wait_seconds elapses.

  Args:
    operation_ref: A Resource created by GetOperationRef describing the
      Operation.
    message: The message to display to the user while they wait.
    has_result: If True, the function will return the target of the operation
      when it completes. If False, nothing will be returned.
    release_track: The release track to use for the API version.
    max_wait: The time to wait for the operation to succeed before timing out.

  Returns:
    if has_result = True, a RemediationIntent entity.
    Otherwise, None.
  """
  client = GetClientInstance(release_track)
  resource_client = client.organizations_locations_remediationIntents
  operations_client = client.organizations_locations_operations
  if has_result:
    poller = waiter.CloudOperationPoller(
        resource_client, operations_client
    )
  else:
    # For no result expectations, just operations service client is required.
    poller = waiter.CloudOperationPollerNoResources(operations_client)

  response = waiter.WaitFor(
      poller, operation_ref, message, max_wait_ms=max_wait.seconds * 1000
  )
  return response
