# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud bigquery jobs describe.
"""

from googlecloudsdk.api_lib.bigquery import bigquery
from googlecloudsdk.api_lib.bigquery import job_display
from googlecloudsdk.calliope import base
from googlecloudsdk.core import list_printer


class JobsDescribe(base.Command):
  """Shows information about a specified job.

  The job's job type, state, start time, duration, and number of bytes
  processed are displayed.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument('job_id', help='The ID of the job to be described.')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespeace, All the arguments that were provided to this
        command invocation.

    Raises:
      bigquery.Error: if error is reported by the backend.

    Returns:
      A Job message.
    """
    job = bigquery.Job.ResolveFromId(args.job_id)
    return job.GetRaw()

  def Display(self, args, job):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      job: A Job message.
    """
    info = job_display.DisplayInfo(job)
    # Print information in the form of a one-row table:
    list_printer.PrintResourceList('bigquery.jobs.describe', [info])
