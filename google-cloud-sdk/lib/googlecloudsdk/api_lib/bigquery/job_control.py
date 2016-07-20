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

"""Provides methods for controlling jobs.
"""

import itertools
import logging
import sys
import time

from apitools.base.py import exceptions
from apitools.base.py import transfer

from googlecloudsdk.api_lib.bigquery import bigquery
from googlecloudsdk.api_lib.bigquery import job_ids
from googlecloudsdk.api_lib.bigquery import job_progress


def ExecuteJob(
    apitools_client, messages_module, args, configuration, async=None,
    project_id=None, upload_file=None, job_id=None):
  """Start execution of a job, possibly waiting for results.

  Args:
    apitools_client: The apitools client through which to issue the request.
    messages_module: The module defining messages used in apitools calls.
    args: command-line arguments for the executing command
    configuration: The configuration for a job.
    async: If True, the job will be started and will complete asynchronously;
      otherwise the method call will wait for completion of the job.
    project_id: The project_id to run the job under.
    upload_file: A file to include as a media upload to this request.
      Only valid on job requests that expect a media upload file.
    job_id: A unique job ID to use for this job. If None, a unique job_id will
      be created for this request.

  Returns:
    the job that was started
  """
  if async is None:
    async = args.async

  # Use the default job id generator if no job id was supplied.
  job_id = job_id or args.job_id_generator

  if async:
    job = _StartJob(
        apitools_client, messages_module, configuration,
        project_id=project_id,
        upload_file=upload_file, job_id=job_id)
    _RaiseIfJobError(job)
  else:
    job = _RunJobSynchronously(
        apitools_client, messages_module,
        job_progress.ProgressReporter(args.status), configuration,
        project_id=project_id,
        upload_file=upload_file, job_id=job_id)
  return job


def _StartJob(
    apitools_client, messages_module, configuration, project_id=None,
    # pylint: disable=unused-argument
    upload_file=None,
    job_id=None):
  """Start a job with the given configuration.

  Args:
    apitools_client: The apitools client through which to issue the request.
    messages_module: The module defining messages used in apitools calls.
    configuration: The configuration for a job.
    project_id: The project_id to run the job under.
    upload_file: A file to include as a media upload to this request.
      Only valid on job requests that expect a media upload file.
    job_id: A unique job ID or job-ID generator to use for this job. If a
      job-ID generator, a job id will be generated from the job configuration.
      If None, a unique job_id will be created for this request.

  Returns:
    The job resource returned from the insert job request. If there is an
    error, the jobReference field will still be filled out with the job
    reference used in the request.

  Raises:
    bigquery.ClientConfigurationError: if project_id is None.
  """
  if not project_id:
    raise bigquery.ClientConfigurationError(
        'Cannot start a job without a project id.')

  if isinstance(job_id, job_ids.JobIdGenerator):
    job_id = job_id.Generate(configuration)

  if job_id is not None:
    job_reference = messages_module.JobReference(
        jobId=job_id, projectId=project_id)

  media_upload = (
      upload_file
      and transfer.Upload.FromFile(upload_file,
                                   mime_type='application/octet-stream',
                                   auto_transfer=True))

  job_descriptor = messages_module.Job(
      configuration=configuration, jobReference=job_reference)
  request = messages_module.BigqueryJobsInsertRequest(
      job=job_descriptor,
      projectId=project_id)
  try:
    result = apitools_client.jobs.Insert(request, upload=media_upload)
  except exceptions.HttpError as server_error:
    raise bigquery.Error.ForHttpError(server_error)
  return result


def _RunJobSynchronously(
    apitools_client, messages_module, progress_reporter, configuration,
    project_id=None, upload_file=None, job_id=None):
  result = _StartJob(
      apitools_client, messages_module, configuration, project_id=project_id,
      upload_file=upload_file, job_id=job_id)
  if result.status.state != 'DONE':
    job_reference = result.jobReference
    result = _WaitJob(
        apitools_client, messages_module, job_reference, progress_reporter)
  return _RaiseIfJobError(result)


def _WaitJob(
    apitools_client, messages_module, job_reference, progress_reporter,
    status='DONE', wait=sys.maxint):
  """Poll for a job to run until it reaches the requested status.

  Arguments:
    apitools_client: the client to be used for polling
    messages_module: The module defining messages used in apitools calls.
    job_reference: JobReference to poll.
    progress_reporter: a job_progress.ProgressReporter
      that will be called after each job poll.
    status: (optional, default 'DONE') Desired job status.
    wait: (optional, default maxint) Max wait time.

  Returns:
    The job object returned by the final status call.

  Raises:
    StopIteration: If polling does not reach the desired state before
      timing out.
    ValueError: If given an invalid wait value.
  """
  start_time = time.time()
  job = None

  # This is a first pass at wait logic: we ping at 1s intervals a few
  # times, then increase to max(3, max_wait), and then keep waiting
  # that long until we've run out of time.
  waits = itertools.chain(
      itertools.repeat(1, 8),
      xrange(2, 30, 3),
      itertools.repeat(30))
  current_wait = 0
  current_status = 'UNKNOWN'
  while current_wait <= wait:
    try:
      done, job = _PollJob(
          apitools_client, messages_module, job_reference, status=status,
          wait=wait)
      current_status = job.status.state
      if done:
        progress_reporter.Print(
            job_reference.jobId, current_wait, current_status)
        break
    except bigquery.CommunicationError as e:
      # Communication errors while waiting on a job are okay.
      logging.warning('Transient error during job status check: %s', e)
    except bigquery.BackendError as e:
      # Temporary server errors while waiting on a job are okay.
      logging.warning('Transient error during job status check: %s', e)
    for _ in xrange(waits.next()):
      current_wait = time.time() - start_time
      progress_reporter.Print(job_reference.jobId, current_wait, current_status)
      time.sleep(1)
  else:
    raise StopIteration(
        'Wait timed out. Operation not finished, in state {0}'.format(
            current_status))
  progress_reporter.Done()
  return job


def _PollJob(
    apitools_client, messages_module, job_reference, status='DONE', wait=0):
  """Poll a job once for a specific status.

  Arguments:
    apitools_client: Client to be used for the poll.
    messages_module: The module defining messages used in apitools calls.
    job_reference: JobReference to poll.
    status: (optional, default 'DONE') Desired job status.
    wait: (optional, default 0) Max server-side wait time for one poll call.

  Returns:
    Tuple (in_state, job) where in_state is True if job is
    in the desired state.

  Raises:
    ValueError: If given an invalid wait value.
  """
  try:
    int(wait)
  except ValueError:
    raise ValueError('Invalid value for wait: {0}'.format(wait))
  request = messages_module.BigqueryJobsGetRequest(
      jobId=job_reference.jobId,
      projectId=job_reference.projectId)
  job = apitools_client.jobs.Get(request)
  current = job.status.state
  return (current == status, job)


def _RaiseIfJobError(job):
  """Raises a BigQueryError if the job is in an error state.

  Args:
    job: a Job resource.

  Returns:
    job, if it is not in an error state.

  Raises:
    bigquery.Error: A Error instance based on the job's error
    description.
  """
  if IsFailedJob(job):
    error = job.status.errorResult
    raise bigquery.Error.Create(
        _DictForErrorProto(job.status.errorResult),
        None,
        [_DictForErrorProto(error) for error in job.status.errors],
        job.jobReference)
  return job


def _DictForErrorProto(error_proto):
  return {
      'reason': error_proto.reason,
      'message': error_proto.message,
      'debugInfo': error_proto.debugInfo,
      'location': error_proto.location}


def IsFailedJob(job):
  """Predicate to determine whether or not a job failed."""
  return job.status.errorResult is not None
