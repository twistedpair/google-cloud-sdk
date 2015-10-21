# Copyright 2015 Google Inc. All Rights Reserved.

"""Wait for a job to complete."""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import log

from googlecloudsdk.dataproc.lib import util


class Wait(base.Command):
  """View the output of a job as it runs or after it completes."""

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To view the output of a job as it runs, run:

            $ {command} job_id
          """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'id',
        metavar='JOB_ID',
        help='The ID of the job to wait.')

  @util.HandleHttpError
  def Run(self, args):
    client = self.context['dataproc_client']
    messages = self.context['dataproc_messages']

    job_ref = util.ParseJob(args.id, self.context)
    request = job_ref.Request()

    job = client.projects_jobs.Get(request)
    # TODO(user) Check if Job is still running and fail or handle 401.

    job = util.WaitForJobTermination(
        job,
        self.context,
        message='Waiting for job completion',
        goal_state=messages.JobStatus.StateValueValuesEnum.DONE,
        stream_driver_log=True)

    log.status.Print('Job [{0}] finished successfully.'.format(args.id))

    return job

  def Display(self, args, result):
    self.format(result)
