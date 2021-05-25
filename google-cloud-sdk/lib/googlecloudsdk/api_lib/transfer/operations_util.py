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
"""Utils for common operations API interactions."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import encoding
from googlecloudsdk.api_lib.transfer import jobs_util
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.command_lib.transfer import name_util
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import progress_tracker
from googlecloudsdk.core.util import retry
from googlecloudsdk.core.util import scaled_integer


def _get_operation_to_poll(job_name, operation_name):
  """Returns operation name or last operation of job name."""
  if (not job_name and not operation_name) or (job_name and operation_name):
    raise ValueError(
        'job_name or operation_name must be provided but not both.')

  if job_name:
    return jobs_util.block_until_operation_created(job_name)
  return operation_name


def _is_operation_in_progress(result, retryer_state):
  """Takes Operation Apitools object and returns if it is not marked done."""
  del retryer_state  # Unused.
  return not result.done


def api_get(name):
  """Returns operation details from API as Apitools object."""
  client = apis.GetClientInstance('storagetransfer', 'v1')
  messages = apis.GetMessagesModule('storagetransfer', 'v1')

  formatted_operation_name = name_util.add_operation_prefix(name)
  return client.transferOperations.Get(
      messages.StoragetransferTransferOperationsGetRequest(
          name=formatted_operation_name))


def block_until_done(job_name=None, operation_name=None):
  """Does not return until API responds that operation is done.

  Args:
    job_name (str|None): If provided, poll job's last operation.
    operation_name (str|None): Poll this operation name.

  Raises:
    ValueError: One of job_name or operation_name must be provided.
  """
  with progress_tracker.ProgressTracker(message='Waiting for operation'):
    polling_operation_name = _get_operation_to_poll(job_name, operation_name)

    retry.Retryer().RetryOnResult(
        api_get,
        args=[polling_operation_name],
        should_retry_if=_is_operation_in_progress,
        sleep_ms=(
            properties.VALUES.transfer.no_async_polling_interval_ms.GetInt()),
    )


def _call_api_get_and_print_progress(name):
  """Gets operation from API and prints its progress updating in-place."""
  operation = api_get(name)
  metadata = encoding.MessageToDict(operation.metadata)

  if ('counters' in metadata and 'bytesCopiedToSink' in metadata['counters'] and
      'bytesFoundFromSource' in metadata['counters']):
    copied_bytes = metadata['counters']['bytesCopiedToSink']
    total_bytes = metadata['counters']['bytesFoundFromSource']
    progress_percent = int(round(copied_bytes / total_bytes, 2) * 100)
    progress_string = '{}% ({} of {})'.format(
        progress_percent,
        scaled_integer.FormatBinaryNumber(copied_bytes, decimal_places=2),
        scaled_integer.FormatBinaryNumber(total_bytes, decimal_places=2))
  else:
    progress_string = 'UNKNOWN'

  if 'errorBreakdowns' in metadata:
    error_count = sum(
        [error['errorCount'] for error in metadata['errorBreakdowns']])
  else:
    error_count = 0

  log.status.Print(('Status: {} | Progress: {} | Errors: {}\r').format(
      metadata['status'], progress_string, error_count))
  return operation


def _print_progress(name):
  """Prints progress of operation and blocks until transfer is complete.

  Args:
    name (str|None): Poll this operation name.

  Returns:
    Apitools Operation object containing the completed operation's metadata.
  """
  return retry.Retryer(jitter_ms=0).RetryOnResult(
      _call_api_get_and_print_progress,
      args=[name],
      should_retry_if=_is_operation_in_progress,
      sleep_ms=1000)


def display_monitoring_view(name):
  """Prints and updates operation statistics, blocking until copy complete."""
  initial_operation = api_get(name)
  initial_metadata = encoding.MessageToDict(initial_operation.metadata)

  log.status.Print('Operation name: ' +
                   name_util.remove_operation_prefix(initial_operation.name))
  log.status.Print(
      'Parent job: ' +
      name_util.remove_job_prefix(initial_metadata['transferJobName']))
  if 'startTime' in initial_metadata:
    log.status.Print('Start time: ' + initial_metadata['startTime'])

  final_operation = _print_progress(initial_operation.name)
  final_metadata = encoding.MessageToDict(final_operation.metadata)

  if 'endTime' in final_metadata:
    log.status.Print('End time: ' + final_metadata['endTime'])
