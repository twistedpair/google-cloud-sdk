# Copyright 2015 Google Inc. All Rights Reserved.

"""'logging metrics describe' command."""

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.third_party.apitools.base import py as apitools_base

from googlecloudsdk.logging.lib import util


class Describe(base.Command):
  """Shows the definition of a logs-based metric."""

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        'metric_name', help='The name of the metric.')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      The specified metric with its description and configured filter.
    """
    client = self.context['logging_client']
    messages = self.context['logging_messages']
    project = properties.VALUES.core.project.Get(required=True)

    try:
      return client.projects_metrics.Get(
          messages.LoggingProjectsMetricsGetRequest(
              metricsId=args.metric_name,
              projectsId=project))
    except apitools_base.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))

  def Display(self, unused_args, result):
    """This method is called to print the result of the Run() method.

    Args:
      unused_args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    self.format(result)

Describe.detailed_help = {
    'DESCRIPTION': """\
        Shows the definition of a logs-based metric.
    """,
    'EXAMPLES': """\
        To show the definition of a metric called high_severity_count, run:

          $ {command} high_severity_count
    """,
}
