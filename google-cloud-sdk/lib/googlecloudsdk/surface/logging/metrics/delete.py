# Copyright 2015 Google Inc. All Rights Reserved.

"""'logging metrics delete' command."""

from googlecloudsdk.api_lib.logging import util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io
from googlecloudsdk.third_party.apitools.base import py as apitools_base


class Delete(base.Command):
  """Deletes a logs-based metric."""

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        'metric_name', help='The name of the metric to delete.')

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
        'Really delete metric [%s]?' % args.metric_name):
      raise exceptions.ToolException('action canceled by user')
    try:
      unused_result = client.projects_metrics.Delete(
          messages.LoggingProjectsMetricsDeleteRequest(
              metricsId=args.metric_name,
              projectsId=project))
      log.DeletedResource(args.metric_name)
    except apitools_base.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))

Delete.detailed_help = {
    'DESCRIPTION': """\
        Deletes a logs-based metric called high_severity_count.
    """,
    'EXAMPLES': """\
        To delete a metric called high_severity_count, run:

          $ {command} high_severity_count
    """,
}
