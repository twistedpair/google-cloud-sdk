# Copyright 2014 Google Inc. All Rights Reserved.

"""'logging sinks delete' command."""

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io
from googlecloudsdk.third_party.apitools.base import py as apitools_base

from googlecloudsdk.logging.lib import util


class Delete(base.Command):
  """Deletes all entries from a log."""

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument('log_name', help='Log name.')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.
    """
    client = self.context['logging_client']
    messages = self.context['logging_messages']
    project = properties.VALUES.core.project.Get(required=True)

    if not console_io.PromptContinue(
        'Really delete all log entries from [%s]?' % args.log_name):
      raise exceptions.ToolException('action canceled by user')
    try:
      client.projects_logs.Delete(
          messages.LoggingProjectsLogsDeleteRequest(
              projectsId=project, logsId=args.log_name))
      log.DeletedResource(args.log_name)
    except apitools_base.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))


Delete.detailed_help = {
    'DESCRIPTION': """\
        {index}
        With no entries, the log will not appear in the list of your
        project's logs. However, you can write new entries to the log.
    """,
}
