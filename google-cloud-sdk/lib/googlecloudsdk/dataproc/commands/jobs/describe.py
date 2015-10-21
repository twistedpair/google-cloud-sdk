# Copyright 2015 Google Inc. All Rights Reserved.

"""Describe job command."""

from googlecloudsdk.calliope import base

from googlecloudsdk.dataproc.lib import util


class Describe(base.Command):
  """View the details of a job."""

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To view the details of a job, run:

            $ {command} job_id
          """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'id',
        metavar='JOB_ID',
        help='The ID of the job to describe.')

  @util.HandleHttpError
  def Run(self, args):
    client = self.context['dataproc_client']

    job_ref = util.ParseJob(args.id, self.context)
    request = job_ref.Request()

    job = client.projects_jobs.Get(request)
    return job

  def Display(self, args, result):
    self.format(result)
