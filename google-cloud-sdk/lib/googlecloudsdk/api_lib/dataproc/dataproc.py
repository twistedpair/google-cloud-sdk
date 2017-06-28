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

"""Common stateful utilities for the gcloud dataproc tool."""

import time
import urlparse

from apitools.base.py import encoding
from apitools.base.py import exceptions as apitools_exceptions

from googlecloudsdk.api_lib.dataproc import constants
from googlecloudsdk.api_lib.dataproc import exceptions
from googlecloudsdk.api_lib.dataproc import storage_helpers
from googlecloudsdk.api_lib.dataproc import util
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.console import console_attr
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.console import progress_tracker


class Dataproc(object):
  """Stateful utility for calling Dataproc APIs.

  While this currently could all be static. It is encapsulated in a class to
  support API version switching in future.
  """

  def __init__(self):
    super(Dataproc, self).__init__()

  @property
  def client(self):
    return apis.GetClientInstance('dataproc', 'v1')

  @property
  def messages(self):
    return self.client.MESSAGES_MODULE

  @property
  def resources(self):
    return resources.REGISTRY

  # TODO(b/36056506): Use api_lib.utils.waiter
  def WaitForOperation(
      self, operation, message, timeout_s, poll_period_s=5):
    """Poll dataproc Operation until its status is done or timeout reached.

    Args:
      operation: Operation, message of the operation to be polled.
      message: str, message to display to user while polling.
      timeout_s: number, seconds to poll with retries before timing out.
      poll_period_s: number, delay in seconds between requests.

    Returns:
      Operation: the return value of the last successful operations.get
      request.

    Raises:
      OperationError: if the operation times out or finishes with an error.
    """
    request = self.messages.DataprocProjectsRegionsOperationsGetRequest(
        name=operation.name)
    log.status.Print('Waiting on operation [{0}].'.format(operation.name))
    start_time = time.time()
    warnings_so_far = 0
    is_tty = console_io.IsInteractive(error=True)
    tracker_separator = '\n' if is_tty else ''
    def _LogWarnings(warnings):
      new_warnings = warnings[warnings_so_far:]
      if new_warnings:
        # Drop a line to print nicely with the progress tracker.
        log.err.write(tracker_separator)
        for warning in new_warnings:
          log.warn(warning)

    with progress_tracker.ProgressTracker(message, autotick=True):
      while timeout_s > (time.time() - start_time):
        try:
          operation = self.client.projects_regions_operations.Get(request)
          metadata = self.ParseOperationJsonMetadata(operation.metadata)
          _LogWarnings(metadata.warnings)
          warnings_so_far = len(metadata.warnings)
          if operation.done:
            break
        except apitools_exceptions.HttpError:
          # Keep trying until we timeout in case error is transient.
          pass
        time.sleep(poll_period_s)
    metadata = self.ParseOperationJsonMetadata(operation.metadata)
    _LogWarnings(metadata.warnings)
    if not operation.done:
      raise exceptions.OperationTimeoutError(
          'Operation [{0}] timed out.'.format(operation.name))
    elif operation.error:
      raise exceptions.OperationError(
          'Operation [{0}] failed: {1}.'.format(
              operation.name, util.FormatRpcError(operation.error)))

    log.info('Operation [%s] finished after %.3f seconds',
             operation.name, (time.time() - start_time))
    return operation

  class NoOpProgressDisplay(object):
    """For use in place of a ProgressTracker in a 'with' block."""

    def __enter__(self):
      pass

    def __exit__(self, *unused_args):
      pass

  def WaitForJobTermination(
      self,
      job,
      message,
      goal_state,
      stream_driver_log=False,
      log_poll_period_s=1,
      dataproc_poll_period_s=10,
      timeout_s=None):
    """Poll dataproc Job until its status is terminal or timeout reached.

    Args:
      job: The job to wait to finish.
      message: str, message to display to user while polling.
      goal_state: JobStatus.StateValueValuesEnum, the state to define success
      stream_driver_log: bool, Whether to show the Job's driver's output.
      log_poll_period_s: number, delay in seconds between checking on the log.
      dataproc_poll_period_s: number, delay in seconds between requests to
          the Dataproc API.
      timeout_s: number, time out for job completion. None means no timeout.

    Returns:
      Operation: the return value of the last successful operations.get
      request.

    Raises:
      OperationError: if the operation times out or finishes with an error.
    """
    job_ref = self.ParseJob(job.reference.jobId)
    request = self.messages.DataprocProjectsRegionsJobsGetRequest(
        projectId=job_ref.projectId,
        region=job_ref.region,
        jobId=job_ref.jobId)
    driver_log_stream = None
    last_job_poll_time = 0
    job_complete = False
    wait_display = None
    driver_output_uri = None

    def ReadDriverLogIfPresent():
      if driver_log_stream and driver_log_stream.open:
        # TODO(b/36049794): Don't read all output.
        driver_log_stream.ReadIntoWritable(log.err)

    def PrintEqualsLine():
      attr = console_attr.GetConsoleAttr()
      log.err.Print('=' * attr.GetTermSize()[0])

    if stream_driver_log:
      log.status.Print('Waiting for job output...')
      wait_display = self.NoOpProgressDisplay()
    else:
      wait_display = progress_tracker.ProgressTracker(message, autotick=True)
    start_time = now = time.time()
    with wait_display:
      while not timeout_s or timeout_s > (now - start_time):
        # Poll logs first to see if it closed.
        ReadDriverLogIfPresent()
        log_stream_closed = driver_log_stream and not driver_log_stream.open
        if (not job_complete
            and job.status.state in constants.TERMINAL_JOB_STATES):
          job_complete = True
          # Wait an 10s to get trailing output.
          timeout_s = now - start_time + 10

        if job_complete and (not stream_driver_log or log_stream_closed):
          # Nothing left to wait for
          break

        regular_job_poll = (
            not job_complete
            # Poll less frequently on dataproc API
            and now >= last_job_poll_time + dataproc_poll_period_s)
        # Poll at regular frequency before output has streamed and after it has
        # finished.
        expecting_output_stream = stream_driver_log and not driver_log_stream
        expecting_job_done = not job_complete and log_stream_closed
        if regular_job_poll or expecting_output_stream or expecting_job_done:
          last_job_poll_time = now
          try:
            job = self.client.projects_regions_jobs.Get(request)
          except apitools_exceptions.HttpError as error:
            log.warn('GetJob failed:\n{1}', error)
            # Keep trying until we timeout in case error is transient.
          if (stream_driver_log
              and job.driverOutputResourceUri
              and job.driverOutputResourceUri != driver_output_uri):
            if driver_output_uri:
              PrintEqualsLine()
              log.warn("Job attempt failed. Streaming new attempt's output.")
              PrintEqualsLine()
            driver_output_uri = job.driverOutputResourceUri
            driver_log_stream = storage_helpers.StorageObjectSeriesStream(
                job.driverOutputResourceUri)
        time.sleep(log_poll_period_s)
        now = time.time()

    # TODO(b/34836493): Get better test coverage of the next 20 lines.
    state = job.status.state
    if state is not goal_state and job.status.details:
      # Just log details, because the state will be in the error message.
      log.info(job.status.details)

    if state in constants.TERMINAL_JOB_STATES:
      if stream_driver_log:
        if not driver_log_stream:
          log.warn('Expected job output not found.')
        elif driver_log_stream.open:
          log.warn('Job terminated, but output did not finish streaming.')
      if state is goal_state:
        return job
      raise exceptions.JobError(
          'Job [{0}] entered state [{1}] while waiting for [{2}].'.format(
              job_ref.jobId, state, goal_state))
    raise exceptions.JobTimeoutError(
        'Job [{0}] timed out while in state [{1}].'.format(
            job_ref.jobId, state))

  def ParseCluster(self, name):
    """Parse Cluster name, ID, or URL into Cloud SDK reference."""
    ref = self.resources.Parse(
        name,
        params={
            'region': properties.VALUES.dataproc.region.GetOrFail,
            'projectId': properties.VALUES.core.project.GetOrFail
        },
        collection='dataproc.projects.regions.clusters')
    return ref

  def ParseJob(self, job_id):
    """Parse Job name, ID, or URL into Cloud SDK reference."""
    ref = self.resources.Parse(
        job_id,
        params={
            'region': properties.VALUES.dataproc.region.GetOrFail,
            'projectId': properties.VALUES.core.project.GetOrFail
        },
        collection='dataproc.projects.regions.jobs')
    return ref

  def ParseOperation(self, operation):
    """Parse Operation name, ID, or URL into Cloud SDK reference."""
    collection = 'dataproc.projects.regions.operations'
    # Dataproc usually refers to Operations by relative name, which must be
    # parsed explicitly until self.resources.Parse supports it.
    # TODO(b/36055864): Remove once Parse delegates to ParseRelativeName.
    url = urlparse.urlparse(operation)
    if not url.scheme and '/' in url.path and not url.path.startswith('/'):
      return self.resources.ParseRelativeName(operation, collection=collection)
    return self.resources.Parse(
        operation,
        params={
            'regionsId': properties.VALUES.dataproc.region.GetOrFail,
            'projectsId': properties.VALUES.core.project.GetOrFail
        },
        collection=collection)

  def ParseOperationJsonMetadata(self, metadata_value):
    if not metadata_value:
      return self.messages.ClusterOperationMetadata()
    return encoding.JsonToMessage(
        self.messages.ClusterOperationMetadata,
        encoding.MessageToJson(metadata_value))
