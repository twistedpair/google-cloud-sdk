# Copyright 2015 Google Inc. All Rights Reserved.

"""'logging metrics list' command."""

from googlecloudsdk.api_lib.logging import util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import properties
from googlecloudsdk.third_party.apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.third_party.apitools.base.py import list_pager


class List(base.Command):
  """Displays all logs-based metrics."""

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        '--limit', required=False, type=int, default=None,
        help='If greater than zero, the maximum number of results.')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      The list of metrics.
    """
    client = self.context['logging_client_v1beta3']
    messages = self.context['logging_messages_v1beta3']
    project = properties.VALUES.core.project.Get(required=True)

    if args.limit <= 0:
      args.limit = None

    request = messages.LoggingProjectsMetricsListRequest(projectsId=project)

    return list_pager.YieldFromList(
        client.projects_metrics, request, field='metrics', limit=args.limit,
        batch_size=None, batch_size_attribute='pageSize')

  def Display(self, unused_args, result):
    """This method is called to print the result of the Run() method.

    Args:
      unused_args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    try:
      list_printer.PrintResourceList('logging.metrics', result)
    except apitools_exceptions.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))

List.detailed_help = {
    'DESCRIPTION': """\
        Lists all logs-based metrics.
    """,
    'EXAMPLES': """\
          $ {command} --limit=10
    """,
}
