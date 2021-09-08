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

import re

from apitools.base.py import encoding
from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.functions.v2 import exceptions
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base as calliope_base
from googlecloudsdk.core.console import progress_tracker
from googlecloudsdk.core.util import retry

import six

_API_NAME = 'cloudfunctions'

_RELEASE_TRACK_TO_API_VERSION = {
    calliope_base.ReleaseTrack.ALPHA: 'v2alpha',
    calliope_base.ReleaseTrack.BETA: 'v2beta',
    calliope_base.ReleaseTrack.GA: 'v2'
}

MAX_WAIT_MS = 1820000
SLEEP_MS = 1000

# TODO(b/197300386) this util is using v2alpha specific deserializations/enums


def GetMessagesModule(release_track):
  """Returns the API messages module for GCFv2."""
  api_version = _RELEASE_TRACK_TO_API_VERSION.get(release_track)
  return apis.GetMessagesModule(_API_NAME, api_version)


def GetClientInstance(release_track):
  """Returns an API client for GCFv2."""
  api_version = _RELEASE_TRACK_TO_API_VERSION.get(release_track)
  return apis.GetClientInstance(_API_NAME, api_version)


def GetStateMessagesStrings(state_messages):
  """Returns the list of string representations of the state messages."""
  return map(lambda st: '[{}] {}'.format(str(st.severity), st.message),
             state_messages)


def _GetStageName(name_enum):
  """Converts NameValueValuesEnum into human-readable text."""
  return str(name_enum).replace('_', ' ').title()


def _GetOperationMetadata(messages, operation):
  return encoding.PyValueToMessage(
      messages.GoogleCloudFunctionsV2alphaOperationMetadata,
      encoding.MessageToPyValue(operation.metadata))


def _GetOperation(client, request):
  """Get operation and return None if doesn't exist."""
  try:
    # We got response for a GET request, so an operation exists.
    return client.projects_locations_operations.Get(request)
  except apitools_exceptions.HttpError as error:
    if error.status_code == six.moves.http_client.NOT_FOUND:
      return None
    raise


def _GetStages(client, request, messages):
  """Returns None until stages have been loaded in the operation."""
  operation = _GetOperation(client, request)
  if operation.error:
    raise exceptions.StatusToFunctionsError(operation.error)

  if not operation.metadata:
    return None
  operation_metadata = _GetOperationMetadata(messages, operation)
  if not operation_metadata.stages:
    return None

  stages = []
  for stage in operation_metadata.stages:
    message = '[{}]'.format(_GetStageName(stage.name))
    stages.append(progress_tracker.Stage(message, key=str(stage.name)))
  return stages


def _GetOperationStatus(client, request, tracker, messages):
  """Returns a Boolean indicating whether the request has completed."""
  operation = client.projects_locations_operations.Get(request)
  if operation.error:
    raise exceptions.StatusToFunctionsError(operation.error)

  operation_metadata = _GetOperationMetadata(messages, operation)
  for stage in operation_metadata.stages:
    stage_key = str(stage.name)
    # Start running a stage
    if stage.state == messages.GoogleCloudFunctionsV2alphaStage.StateValueValuesEnum.IN_PROGRESS and not tracker.IsRunning(
        stage_key):
      tracker.StartStage(stage_key)
      tracker.UpdateStage(stage_key, stage.message + '...')
    # Output Build logs URL
    if stage.resourceUri and stage_key == 'BUILD' and tracker.IsRunning(
        stage_key):
      tracker.UpdateStage(
          stage_key, stage.message +
          '... Logs are available at [{}]'.format(stage.resourceUri))
    # Complete a finished stage
    if stage.state == messages.GoogleCloudFunctionsV2alphaStage.StateValueValuesEnum.COMPLETE:
      if tracker.IsWaiting(stage_key):
        tracker.StartStage(stage_key)
      if tracker.IsRunning(stage_key):
        if stage_key == 'BUILD':
          tracker.UpdateStage(
              stage_key, 'Logs are available at [{}]'.format(stage.resourceUri))
        else:
          tracker.UpdateStage(stage_key, '')
        if stage.stateMessages:
          tracker.CompleteStageWithWarnings(
              stage_key, GetStateMessagesStrings(stage.stateMessages))
        else:
          tracker.CompleteStage(stage_key)
  return operation.done


def WaitForOperation(client, messages, operation, description):
  """Wait for a long-running operation (LRO) to complete."""
  request = messages.CloudfunctionsProjectsLocationsOperationsGetRequest(
      name=operation.name)
  # Wait for stages to be loaded.
  with progress_tracker.ProgressTracker('Preparing function') as tracker:
    retryer = retry.Retryer(max_wait_ms=MAX_WAIT_MS)
    try:
      stages = retryer.RetryOnResult(
          _GetStages,
          args=[client, request, messages],
          should_retry_if=None,
          sleep_ms=SLEEP_MS)
    except retry.WaitException:
      raise exceptions.FunctionsError('Operation {0} is taking too long'.format(
          request.name))

  # Wait for LRO to complete.
  description += '...'
  with progress_tracker.StagedProgressTracker(description, stages) as tracker:
    retryer = retry.Retryer(max_wait_ms=MAX_WAIT_MS)
    try:
      retryer.RetryOnResult(
          _GetOperationStatus,
          args=[client, request, tracker, messages],
          should_retry_if=False,
          sleep_ms=SLEEP_MS)
    except retry.WaitException:
      raise exceptions.FunctionsError('Operation {0} is taking too long'.format(
          request.name))


def FormatTimestamp(timestamp):
  """Formats a timestamp which will be presented to a user.

  Args:
    timestamp: Raw timestamp string in RFC3339 UTC "Zulu" format.

  Returns:
    Formatted timestamp string.
  """
  return re.sub(r'(\.\d{3})\d*Z$', r'\1', timestamp.replace('T', ' '))
