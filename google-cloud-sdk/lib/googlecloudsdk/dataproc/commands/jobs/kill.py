# Copyright 2015 Google Inc. All Rights Reserved.

"""Kill job command."""

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io

from googlecloudsdk.dataproc.lib import util


class Kill(base.Command):
  """Kill an active job."""

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To cancel a job, run:

            $ {command} job_id
          """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'id',
        metavar='JOB_ID',
        help='The ID of the job to kill.')

  @util.HandleHttpError
  def Run(self, args):
    client = self.context['dataproc_client']
    messages = self.context['dataproc_messages']

    job_ref = util.ParseJob(args.id, self.context)
    request = messages.DataprocProjectsJobsCancelRequest(
        projectId=job_ref.projectId,
        jobId=job_ref.jobId,
        cancelJobRequest=messages.CancelJobRequest())

    # TODO(user) Check if Job is still running and fail or handle 401.

    if not console_io.PromptContinue(
        message="The job '{0}' will be killed.".format(args.id)):
      raise exceptions.ToolException('Cancellation aborted by user.')

    job = client.projects_jobs.Cancel(request)
    log.status.Print(
        'Job cancellation initiated for [{0}].'.format(job_ref.jobId))

    job = util.WaitForJobTermination(
        job,
        self.context,
        message='Waiting for job cancellation',
        goal_state=messages.JobStatus.StateValueValuesEnum.CANCELLED)

    log.status.Print('Killed [{0}].'.format(job_ref))

    return job

  def Display(self, args, result):
    self.format(result)
