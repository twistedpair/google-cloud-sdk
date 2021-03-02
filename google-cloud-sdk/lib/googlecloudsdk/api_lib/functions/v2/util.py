# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Functionality related to Cloud Functions v2 API clients."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from googlecloudsdk.api_lib.functions.v2 import exceptions
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base as calliope_base
from googlecloudsdk.core.console import progress_tracker
from googlecloudsdk.core.util import retry

_API_NAME = 'cloudfunctions'

_RELEASE_TRACK_TO_API_VERSION = {
    calliope_base.ReleaseTrack.ALPHA: 'v2alpha',
    calliope_base.ReleaseTrack.BETA: 'v2beta',
    calliope_base.ReleaseTrack.GA: 'v2'
}

MAX_WAIT_MS = 1820000
WAIT_CEILING_MS = 2000
SLEEP_MS = 1000


def GetMessagesModule(release_track):
  """Returns the API messages module for GCFv2."""
  api_version = _RELEASE_TRACK_TO_API_VERSION.get(release_track)
  return apis.GetMessagesModule(_API_NAME, api_version)


def GetClientInstance(release_track):
  """Returns an API client for GCFv2."""
  api_version = _RELEASE_TRACK_TO_API_VERSION.get(release_track)
  return apis.GetClientInstance(_API_NAME, api_version)


def _GetOperationStatus(client, request, tracker):
  """Returns a Boolean indicating whether the request has completed."""
  if tracker:
    tracker.Tick()
  op = client.projects_locations_operations.Get(request)
  if op.error:
    raise exceptions.FunctionsError(op)
  return op.done


def WaitForOperation(client, messages, operation, description):
  """Wait for a long-running operation (LRO) to complete."""
  request = messages.CloudfunctionsProjectsLocationsOperationsGetRequest(
      name=operation.name)

  with progress_tracker.ProgressTracker(description, autotick=False) as tracker:
    # This is actually linear retryer.
    retryer = retry.Retryer(
        exponential_sleep_multiplier=1,
        max_wait_ms=MAX_WAIT_MS,
        wait_ceiling_ms=WAIT_CEILING_MS)
    try:
      retryer.RetryOnResult(
          _GetOperationStatus,
          args=[client, request, tracker],
          should_retry_if=False,
          sleep_ms=SLEEP_MS)
    except retry.WaitException:
      raise exceptions.FunctionsError('Operation {0} is taking too long'.format(
          request.name))
