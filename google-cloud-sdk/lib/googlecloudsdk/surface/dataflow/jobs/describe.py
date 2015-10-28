# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud dataflow jobs describe command.
"""

from googlecloudsdk.api_lib.dataflow import job_utils
from googlecloudsdk.calliope import base


class Describe(base.Command):
  """Outputs the Job object resulting from the Get API.

  By default this will display the Summary view which includes:
    - Project ID
    - Job ID
    - Job Name
    - Job Type (Batch vs. Streaming)
    - Job Create Time
    - Job Status (Running, Done, Cancelled, Failed)
    - Job Status Time

  Notable values that are only in the full view:
    - Environment (staging Jars, information about workers, etc.)
    - Steps from the workflow graph
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command.

    Args:
      parser: argparse.ArgumentParser to register arguments with.
    """
    job_utils.ArgsForJobRef(parser)

    parser.add_argument(
        '--full', action='store_const',
        const=job_utils.JOB_VIEW_ALL,
        default=job_utils.JOB_VIEW_SUMMARY,
        help='Retrieve the full Job rather than the summary view')

  def Run(self, args):
    """Runs the command.

    Args:
      args: The arguments that were provided to this command invocation.

    Returns:
      A Job message.
    """
    return job_utils.GetJobForArgs(self.context, args, args.full, required=True)

  def Display(self, args, job):
    """This method is called to print the result of the Run() method.

    Args:
      args: all the arguments that were provided to this command invocation.
      job: The Job message returned from the Run() method.
    """
    self.format(job)
