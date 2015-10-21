# Copyright 2015 Google Inc. All Rights Reserved.

"""The command group for cloud dataproc jobs."""

from googlecloudsdk.calliope import base


class Jobs(base.Group):
  """Submit and manage Google Cloud Dataproc jobs."""

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To learn about the types of jobs that can be submitted, run:

            $ {command} submit

          To view the output of a job as it runs, run:

            $ {command} wait job_id

          To cancel an active job, run:

            $ {command} kill job_id

          To view the details of a job, run:

            $ {command} describe job_id

          To see the list of all jobs, run:

            $ {command} list

          To delete the record of an inactive job, run:

            $ {command} delete job_id
          """,
  }
