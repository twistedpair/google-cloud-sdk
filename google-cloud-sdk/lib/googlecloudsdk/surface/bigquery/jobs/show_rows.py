# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud bigquery jobs show-rows.
"""

from googlecloudsdk.api_lib.bigquery import bigquery
from googlecloudsdk.calliope import base
from googlecloudsdk.core.console import console_io


class JobsShowRows(base.Command):
  """Displays selected rows in the result of a query job.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        '--limit',
        type=int,
        default=bigquery.DEFAULT_RESULTS_LIMIT,
        help='The maximum number of rows to display.')
    parser.add_argument(
        '--start-row',
        type=int,
        default=0,
        help='The number of rows to skip before showing table data.')
    parser.add_argument('job_id', help='The job ID of the asynchronous query.')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace, All the arguments that were provided to this
        command invocation.

    Returns:
      A bigquery.QueryResults object.
    """
    job = bigquery.Job.ResolveFromId(args.job_id)
    return job.GetQueryResults(start_row=args.start_row, max_rows=args.limit)

  def Display(self, args, query_results):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that the command was run with.
      query_results: A bigquery.QueryResults object.
    """
    console_io.PrintExtendedList(query_results,
                                 query_results.GetColumnFetchers())

