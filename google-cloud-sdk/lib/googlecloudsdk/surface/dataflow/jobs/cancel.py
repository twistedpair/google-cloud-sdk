# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud dataflow jobs cancel command.
"""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.shared.dataflow import job_utils
from googlecloudsdk.surface import dataflow as commands
from googlecloudsdk.third_party.apitools.base import py as apitools_base


class Cancel(base.Command):
  """Cancels all jobs that match the command line arguments.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    job_utils.ArgsForJobRefs(parser, nargs='+')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: all the arguments that were provided to this command invocation.

    Returns:
      A pair of lists indicating the jobs that were successfully cancelled and
      those that failed to be cancelled.
    """
    for job_ref in job_utils.ExtractJobRefs(self.context, args):
      self._CancelJob(job_ref)
    return None

  def _CancelJob(self, job_ref):
    """Cancels a job.

    Args:
      job_ref: resources.Resource, The reference to the job to cancel.
    """
    apitools_client = self.context[commands.DATAFLOW_APITOOLS_CLIENT_KEY]
    dataflow_messages = self.context[commands.DATAFLOW_MESSAGES_MODULE_KEY]

    request = dataflow_messages.DataflowProjectsJobsUpdateRequest(
        projectId=job_ref.projectId,
        jobId=job_ref.jobId,
        # We don't need to send the full job, because only the state can be
        # updated, and the other fields are ignored.
        job=dataflow_messages.Job(
            requestedState=(dataflow_messages.Job.RequestedStateValueValuesEnum
                            .JOB_STATE_CANCELLED)))

    try:
      apitools_client.projects_jobs.Update(request)
      log.status.Print('Cancelled job [{0}]'.format(job_ref.jobId))
    except apitools_base.HttpError as unused_error:
      log.err.Print('Failed to cancel job [{0}]'.format(job_ref.jobId))
