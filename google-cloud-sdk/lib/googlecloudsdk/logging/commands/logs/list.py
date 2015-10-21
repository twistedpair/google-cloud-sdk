# Copyright 2014 Google Inc. All Rights Reserved.

"""'logging logs list' command."""

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io
from googlecloudsdk.third_party.apitools.base import py as apitools_base
from googlecloudsdk.third_party.apitools.base.py import list_pager

from googlecloudsdk.logging.lib import util


class List(base.Command):
  """Lists your project's logs."""

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        '--limit', required=False, type=int, default=0,
        help='If greater than zero, the maximum number of results.')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      The list of logs.
    """
    client = self.context['logging_client']
    messages = self.context['logging_messages']
    project = properties.VALUES.core.project.Get(required=True)

    if args.limit <= 0:
      args.limit = None

    request = messages.LoggingProjectsLogsListRequest(projectsId=project)

    return list_pager.YieldFromList(
        client.projects_logs, request, field='logs', limit=args.limit,
        batch_size=None, batch_size_attribute='pageSize')

  def Display(self, unused_args, result):
    """This method is called to print the result of the Run() method.

    Args:
      unused_args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    try:
      # Custom selector to return user friendly log names.
      selector = ('NAME', lambda log: util.ExtractLogName(log.name))
      console_io.PrintExtendedList(result, (selector,))
    except apitools_base.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))

List.detailed_help = {
    'DESCRIPTION': """\
        {index}
        Only logs that contain log entries are listed.
    """,
}
