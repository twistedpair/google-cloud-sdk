# Copyright 2015 Google Inc. All Rights Reserved.
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

"""Utilities to support long running operations."""

import abc
import sys
import time

from googlecloudsdk.core import exceptions
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core.console import progress_tracker
from googlecloudsdk.core.util import retry


class TimeoutError(exceptions.Error):
  pass


class AbortWaitError(exceptions.Error):
  pass


class OperationPoller(object):
  """Interface for defining operation which can be polled and waited on.

  This construct manages operation_ref, operation and result abstract objects.
  Operation_ref is an identifier for operation which is a proxy for result
  object. OperationPoller has three responsibilities:
    1. Given operation object determine if it is done.
    2. Given operation_ref fetch operation object
    3. Given operation object fetch result object
  """
  __metaclass__ = abc.ABCMeta

  # Override any of these settings.
  PRE_START_SLEEP_MS = 1000  # Time to wait before making first poll request.
  MAX_RETRIALS = None  # max number of retrials before raising RetryException.
  MAX_WAIT_MS = 300000  # number of ms to wait before raising WaitException
  EXPONENTIAL_SLEEP_MULTIPLIER = 1.409  # factor to use on subsequent retries
  JITTER_MS = 1000  # random (up to the value) additional sleep between retries
  WAIT_CEILING_MS = 180000  # Maximum wait between retries.
  SLEEP_MS = 2000  # int or iterable, for how long to wait between trials.

  @abc.abstractmethod
  def IsDone(self, operation):
    """Given result of Poll determines if result is done.

    Args:
      operation: object representing operation returned by Poll method.

    Returns:

    """
    return True

  @abc.abstractmethod
  def Poll(self, operation_ref):
    """Retrieves operation given its reference.

    Args:
      operation_ref: str, some id for operation.

    Returns:
      object which represents operation.
    """
    return None

  @abc.abstractmethod
  def GetResult(self, operation):
    """Given operation message retrieves result it represents.

    Args:
      operation: object, representing operation returned by Poll method.
    Returns:
      some object created by given operation.
    """
    return None


def WaitFor(poller, operation_ref, message):
  """Waits with retrues for operation to be done given poller.

  Args:
    poller: OperationPoller, poller to use during retrials.
    operation_ref: object, passed to operation poller poll method.
    message: str, string to display for progrss_tracker.

  Returns:
    poller.GetResult(operation).

  Raises:
    AbortWaitError: if ctrl-c was pressed.
    TimeoutError: if retryer has finished wihout being done.
  """

  def _CtrlCHandler(unused_signal, unused_frame):
    raise AbortWaitError('Ctrl-C aborted wait.')

  try:
    with execution_utils.CtrlCSection(_CtrlCHandler):
      try:
        with progress_tracker.ProgressTracker(message) as tracker:

          if poller.PRE_START_SLEEP_MS:
            _SleepMs(poller.PRE_START_SLEEP_MS)

          def _StatusUpdate(unused_result, unused_status):
            tracker.Tick()

          retryer = retry.Retryer(
              max_retrials=poller.MAX_RETRIALS,
              max_wait_ms=poller.MAX_WAIT_MS,
              exponential_sleep_multiplier=poller.EXPONENTIAL_SLEEP_MULTIPLIER,
              jitter_ms=poller.JITTER_MS,
              status_update_func=_StatusUpdate)

          def _IsNotDone(operation, unused_state):
            return not poller.IsDone(operation)

          operation = retryer.RetryOnResult(
              func=poller.Poll,
              args=(operation_ref,),
              should_retry_if=_IsNotDone,
              sleep_ms=poller.SLEEP_MS)
      except retry.RetryException:
        raise TimeoutError(
            'Operation {0} has not finished in {1} seconds'
            .format(operation_ref,
                    int(poller.MAX_WAIT_MS / 1000)))
  except AbortWaitError:
    # Write this out now that progress tracker is done.
    sys.stderr.write('Aborting wait for operation {0}.\n'.format(operation_ref))
    raise

  return poller.GetResult(operation)


def _SleepMs(miliseconds):
  time.sleep(miliseconds / 1000)
