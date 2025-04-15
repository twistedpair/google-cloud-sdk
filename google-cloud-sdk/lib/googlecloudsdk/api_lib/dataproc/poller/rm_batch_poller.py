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

"""Waiter utility for api_lib.util.waiter.py."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.dataproc import exceptions
from googlecloudsdk.api_lib.dataproc import util
from googlecloudsdk.api_lib.dataproc.poller import cloud_console_url_helper
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.core import log


class RmBatchPoller(waiter.OperationPoller):
  """Poller for resource manager batches.

  This should be used for spark version 3+, and Ray version 1+.
  """

  def __init__(self, dataproc):
    self.dataproc = dataproc
    self.fist_tick_message_printed = False

  def IsDone(self, batch):
    """See base class."""
    if batch and batch.state in (
        self.dataproc.messages.Batch.StateValueValuesEnum.SUCCEEDED,
        self.dataproc.messages.Batch.StateValueValuesEnum.CANCELLED,
        self.dataproc.messages.Batch.StateValueValuesEnum.FAILED,
    ):
      return True
    return False

  def Poll(self, batch_ref):
    """See base class."""
    request = self.dataproc.messages.DataprocProjectsLocationsBatchesGetRequest(
        name=batch_ref
    )
    try:
      return self.dataproc.client.projects_locations_batches.Get(request)
    except apitools_exceptions.HttpError as error:
      log.warning('Get Batch failed:\n{}'.format(error))
      if util.IsClientHttpException(error):
        # Stop polling if encounter client Http error (4xx).
        raise

  def GetResult(self, batch):
    """Handles errors.

    Error handling for batch jobs. This happen after the batch reaches one of
    the complete states.

    Overrides.

    Args:
      batch: The batch resource.

    Returns:
      None. The result is directly output to log.err.

    Raises:
      JobTimeoutError: When waiter timed out.
      JobError: When remote batch job is failed.
    """
    if not batch:
      # Batch resource is None but polling is considered done.
      # This only happens when the waiter timed out.
      raise exceptions.JobTimeoutError('Timed out while waiting for batch job.')

    if (
        batch.state
        == self.dataproc.messages.Batch.StateValueValuesEnum.CANCELLED
    ):
      log.warning('Batch job is CANCELLED.')
    elif (
        batch.state == self.dataproc.messages.Batch.StateValueValuesEnum.FAILED
    ):
      err_message = 'Batch job is FAILED.'
      if batch.stateMessage:
        err_message = '{} Detail: {}'.format(err_message, batch.stateMessage)
        if err_message[-1] != '.':
          err_message += '.'
      err_message += '\n'
      err_message += (
          'Running auto diagnostics on the batch. It may take few '
          'minutes before diagnostics output is available. Please '
          "check diagnostics output by running 'gcloud dataproc "
          "batches describe' command."
      )
      raise exceptions.JobError(err_message)

    # Nothing to return, since the result is directly output to users.
    return None

  def TrackerUpdateFunction(self, tracker, poll_result, status):
    """Prints links to cloud console after the first success pull."""
    if not self.fist_tick_message_printed:
      self.fist_tick_message_printed = True
      cloud_logging_url = cloud_console_url_helper.get_batch_logging_url(
          poll_result
      )
      dataproc_batch_url = cloud_console_url_helper.get_dataproc_batch_url(
          poll_result
      )
      log_level = log.GetVerbosity()
      log.SetVerbosity(logging.INFO)
      log.info(
          'Please check the driver output in Cloud Logging: %s. (The log can'
          ' take a few minutes to show up.) You can visit the batch resource'
          ' at %s',
          cloud_logging_url,
          dataproc_batch_url,
      )
      log.info('Waiting for the batch to complete.')
      log.SetVerbosity(log_level)
