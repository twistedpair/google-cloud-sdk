# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud bigquery list_projects.
"""

from googlecloudsdk.api_lib.bigquery import bigquery
from googlecloudsdk.calliope import base
from googlecloudsdk.core import list_printer
from googlecloudsdk.surface import bigquery as commands


class ListProjects(base.Command):
  """Lists all the user's projects for which the Big Query API is enabled.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        '--limit',
        type=int,
        default=bigquery.DEFAULT_RESULTS_LIMIT,
        help='The maximum number of projects to list.')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespeace, All the arguments that were provided to this
        command invocation.

    Returns:
      A list of ProjectsValueListEntry objects.
    """
    apitools_client = self.context[commands.APITOOLS_CLIENT_KEY]
    bigquery_messages = self.context[commands.BIGQUERY_MESSAGES_MODULE_KEY]
    request = bigquery_messages.BigqueryProjectsListRequest(
        maxResults=args.limit)
    project_list = apitools_client.projects.List(request)
    return project_list.projects

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The list of ProjectsValueListEntry objects returned from the Run()
        method.
    """
    list_printer.PrintResourceList('bigquery.projects', result)
