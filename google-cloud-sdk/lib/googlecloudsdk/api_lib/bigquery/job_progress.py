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

"""Facilities for displaying status messages with job progress.
"""

from googlecloudsdk.core import log


STATUS_REPORTING_NONE = 'none'
STATUS_REPORTING_CHANGES = 'changes'
STATUS_REPORTING_PERIODIC = 'periodic'


class ProgressReporter(object):
  """Wraps an object implementing the AbstractWaitPrinter interface.

  The object wrapped depends on command-line arguments.
  """

  def __init__(self, status_reporting_mode):
    """Initialize this ProgressReporter based on command-line arguments.

    Args:
      status_reporting_mode: the frequency with which the status of a job being
        waited for is to be reported, one of STATUS_REPORTING_NONE,
        STATUS_REPORTING_CHANGES, or STATUS_REPORTING_PERIODIC
    """

    if status_reporting_mode == STATUS_REPORTING_NONE:
      self._wait_printer = QuietWaitPrinter()
    elif status_reporting_mode == STATUS_REPORTING_CHANGES:
      self._wait_printer = TransitionWaitPrinter()
    else:  # status_reporting_mode == STATUS_REPORTING_PERIODIC
      self._wait_printer = VerboseWaitPrinter()

  def Print(self, job_id, wait_time, status):
    """Prints status for the current job we are waiting on.

    Args:
      job_id: the identifier for this job.
      wait_time: the number of seconds we have been waiting so far.
      status: the status of the job we are waiting for.
    """
    self._wait_printer.Print(job_id, wait_time, status)

  def Done(self):
    """Waiting is done and no more Print calls will be made.
    """
    self._wait_printer.Done()


class AbstractWaitPrinter(object):
  """Base class that defines the AbstractWaitPrinter interface."""

  print_on_done = False

  def Print(self, job_id, wait_time, status):
    """Prints status for the current job we are waiting on.

    Args:
      job_id: the identifier for this job.
      wait_time: the number of seconds we have been waiting so far.
      status: the status of the job we are waiting for.
    """
    raise NotImplementedError('Subclass must implement Print')

  def Done(self):
    """Waiting is done and no more Print calls will be made.

    This function should handle the case of Print not being called.
    """
    if self.print_on_done:
      log.status.Print()


class QuietWaitPrinter(AbstractWaitPrinter):
  """An AbstractWaitPrinter that prints nothing."""

  def Print(self, unused_job_id, unused_wait_time, unused_status):
    """Prints status for the current job we are waiting on.

    Args:
      unused_job_id: the identifier for this job.
      unused_wait_time: the number of seconds we have been waiting so far.
      unused_status: the status of the job we are waiting for.
    """
    pass


class VerboseWaitPrinter(AbstractWaitPrinter):
  """An AbstractWaitPrinter that prints every update."""

  def Print(self, job_id, wait_time, status):
    """Prints status for the current job we are waiting on.

    Args:
      job_id: the identifier for this job.
      wait_time: the number of seconds we have been waiting so far.
      status: the status of the job we are waiting for.
    """
    self.print_on_done = True
    log.status.write(
        '\rWaiting on {job} ... ({seconds}s) Current status: {status:<7}'
        .format(job=job_id, seconds=int(wait_time + 0.5), status=status))
    log.status.flush()


class TransitionWaitPrinter(VerboseWaitPrinter):
  """A AbstractWaitPrinter that only prints status change updates."""

  _previous_status = None

  def Print(self, job_id, wait_time, status):
    """Prints status for the current job we are waiting on.

    Args:
      job_id: the identifier for this job.
      wait_time: the number of seconds we have been waiting so far.
      status: the status of the job we are waiting for.
    """
    if status != self._previous_status:
      self._previous_status = status
      super(TransitionWaitPrinter, self).Print(
          job_id, wait_time, status)
