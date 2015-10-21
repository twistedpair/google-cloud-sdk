# Copyright 2015 Google Inc. All Rights Reserved.

"""Delete job command."""

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io

from googlecloudsdk.dataproc.lib import util


class Delete(base.Command):
  """Delete the record of an inactive job."""

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To delete the record of a job, run:

            $ {command} job_id
          """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'id',
        metavar='JOB_ID',
        help='The ID of the job to delete.')

  @util.HandleHttpError
  def Run(self, args):
    client = self.context['dataproc_client']
    messages = self.context['dataproc_messages']

    job_ref = util.ParseJob(args.id, self.context)
    request = messages.DataprocProjectsJobsDeleteRequest(
        projectId=job_ref.projectId,
        jobId=job_ref.jobId)

    if not console_io.PromptContinue(
        message="The job '{0}' will be deleted.".format(args.id)):
      raise exceptions.ToolException('Deletion aborted by user.')

    client.projects_jobs.Delete(request)
    util.WaitForResourceDeletion(
        client.projects_jobs.Get, job_ref, message='Waiting for job deletion')

    log.DeletedResource(job_ref)
