# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud bigquery jobs wait.
"""

import itertools
import sys
from googlecloudsdk.api_lib.bigquery import bigquery
from googlecloudsdk.api_lib.bigquery import job_control
from googlecloudsdk.api_lib.bigquery import job_display
from googlecloudsdk.api_lib.bigquery import job_progress
from googlecloudsdk.api_lib.bigquery import message_conversions
from googlecloudsdk.calliope import base
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.surface import bigquery as commands
from googlecloudsdk.third_party.apitools.base.py import exceptions


class JobsWait(base.Command):
  """Waits up to a specified number of seconds for a specified job to finish.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        '--changed-status-only',
        action='store_true',
        help='When reporting the progress of the job being waited for, '
        'display only changes in status rather than reporting current status '
        'periodically.')
    parser.add_argument(
        '--ignore-error',
        action='store_true',
        help='Do not exit the command with an error if the job finishes in an '
        'error state. (The default behavior is to exit with an error if the '
        'job finishes in an error state.)')
    parser.add_argument(
        '--max-wait',
        type=int,
        help='The number of seconds after which execution of this command '
        'terminates even if the specified job has not finished. '
        'If not specified, this command waits until the specified job '
        'finishes.')
    parser.add_argument(
        'job_id',
        help='The job ID of the specified job. If this argument is omitted '
        'and there is exactly one running job, that job is used. '
        'It is an error if the argument is omitted and there is not exactly '
        'one running job.')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace, All the arguments that were provided to this
        command invocation.

    Raises:
      bigquery.Error: if no job id was provided and no jobs were running.
      bigquery.TimeoutError: on time out.
    Returns:
      A Job message for the job we were waiting for.
    """
    apitools_client = self.context[commands.APITOOLS_CLIENT_KEY]
    bigquery_messages = self.context[commands.BIGQUERY_MESSAGES_MODULE_KEY]
    resource_parser = self.context[commands.BIGQUERY_REGISTRY_KEY]
    project_id = properties.VALUES.core.project.Get(required=True)

    try:
      max_wait = int(args.max_wait) if args.max_wait else sys.maxint
    except ValueError:
      raise bigquery.ClientError(
          'Invalid wait time: {0}'.format(args.max_wait))

    if args.job_id:
      job_resource = resource_parser.Parse(args.job_id,
                                           collection='bigquery.jobs')
      job_reference = message_conversions.JobResourceToReference(
          bigquery_messages, job_resource)
    else:
      project = bigquery.Project(project_id)
      running_jobs = [
          job for job in project.GetCurrentJobsGenerator()
          if job.state in ('PENDING', 'RUNNING')]
      if len(running_jobs) != 1:
        raise bigquery.Error(
            'No job ID provided, found {0} running jobs'.format(
                len(running_jobs)))
      job_reference = running_jobs[0].jobReference

    start_time = bigquery.CurrentTimeInSec()
    job = None
    progress_reporter = job_progress.ProgressReporter(
        job_progress.STATUS_REPORTING_CHANGES if args.changed_status_only else
        job_progress.STATUS_REPORTING_PERIODIC)

    # Create an iterator for polling intervals that yields 1,1,1,1,1,1,1,1,
    # 2,5,8,11,14,17,20,23,26,29, 30,30,30,...
    polling_intervals = itertools.chain(
        itertools.repeat(1, 8), xrange(2, 30, 3), itertools.repeat(30))

    total_wait_so_far = 0
    current_status = 'UNKNOWN'

    while total_wait_so_far < max_wait:

      try:
        request = bigquery_messages.BigqueryJobsGetRequest(
            projectId=job_reference.projectId, jobId=job_reference.jobId)
        job = apitools_client.jobs.Get(request)
        current_status = job.status.state
        if current_status == 'DONE':
          progress_reporter.Print(
              job_reference.jobId, total_wait_so_far, current_status)
          break
      except exceptions.HttpError as server_error:
        try:
          raise bigquery.Error.ForHttpError(server_error)
        except bigquery.CommunicationError as e:
          # Communication errors while waiting on a job are okay.
          log.status.Print(
              'Transient error during job status check: {0}'.format(e))
        except bigquery.BackendError as e:
          # Temporary server errors while waiting on a job are okay.
          log.status.Print(
              'Transient error during job status check: {0}'.format(e))

      # Every second of this polling interval, update the display of the time
      # waited so far:
      seconds_in_interval = polling_intervals.next()
      total_wait_so_far = bigquery.CurrentTimeInSec() - start_time
      for _ in xrange(seconds_in_interval):
        progress_reporter.Print(
            job_reference.jobId, total_wait_so_far, current_status)
        bigquery.Wait(1)
        total_wait_so_far = bigquery.CurrentTimeInSec() - start_time

    else:
      raise bigquery.TimeoutError(
          ('Wait timed out. Operation not finished, in state {0}'
           .format(current_status)),
          None,
          [])
    progress_reporter.Done()
    return job

  def Display(self, args, job):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      job: A Job message.

    Raises:
      bigquery.BackendError: if job has failed.
    """
    info = job_display.DisplayInfo(job)
    # Print information in the form of a one-row table:
    list_printer.PrintResourceList('bigquery.jobs.wait', [info])
    if job_control.IsFailedJob(job):
      if args.ignore_error:
        log.err.Print(
            '\nFAILURE (ignored): {0}'.format(job.status.errorResult.message))
      else:
        log.err.Print()
        raise bigquery.BackendError(
            job.status.errorResult.message, job.status.errorResult, [],
            job.jobReference)
