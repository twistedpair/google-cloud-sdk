# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud bigquery jobs list.
"""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import properties
from googlecloudsdk.shared.bigquery import bigquery
from googlecloudsdk.shared.bigquery import job_display


class JobsList(base.Command):
  """Lists all jobs in a particular project.

  By default, jobs in the current project are listed; this can be overridden
  with the gcloud --project flag. The job ID, job type, state, start time, and
  duration of all jobs in the project are listed.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        '--all-users',
        action='store_true',
        help=('Whether to display jobs owned by all users in the project. '
              'Default false (boolean)'))
    # TODO(cherba): add back state filter support once b/22224569 is resolved.
    # parser.add_argument(
    #    '--state-filter',
    #    default=['running', 'pending'],
    #    type=arg_parsers.ArgList(choices=['done', 'running', 'pending'],
    #                             min_length=1))
    parser.add_argument(
        '--limit',
        type=int,
        default=bigquery.DEFAULT_RESULTS_LIMIT,
        help='The maximum number of datasets to list')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespeace, All the arguments that were provided to this
        command invocation.

    Returns:
      an iterator over JobsValueListEntry messages
    """
    project = bigquery.Project(
        properties.VALUES.core.project.Get(required=True))
    return project.GetCurrentRawJobsListGenerator(
        all_users=args.all_users,
        max_results=args.limit)

  def Display(self, args, jobs):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      jobs: The iterator over JobsValueListEntry messages returned from the
        Run()
        method.
    """
    list_printer.PrintResourceList(
        'bigquery.jobs.list',
        [job_display.DisplayInfo(entry) for entry in jobs])
