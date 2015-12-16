# Copyright 2015 Google Inc. All Rights Reserved.

"""'logging metrics create' command."""

from googlecloudsdk.api_lib.logging import util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.third_party.apitools.base import py as apitools_base


class Create(base.Command):
  """Creates a logs-based metric."""

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument('metric_name', help='The name of the new metric.')
    parser.add_argument('description', help='The metric\'s description.')
    parser.add_argument('filter', help='The metric\'s filter expression.')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      The created metric.
    """
    client = self.context['logging_client']
    messages = self.context['logging_messages']
    metric_filter = args.filter
    # This prevents a clash with the Cloud SDK --filter flag.
    args.filter = None
    project = properties.VALUES.core.project.Get(required=True)
    new_metric = messages.LogMetric(name=args.metric_name,
                                    description=args.description,
                                    filter=metric_filter)
    try:
      result = client.projects_metrics.Create(
          messages.LoggingProjectsMetricsCreateRequest(
              projectsId=project, logMetric=new_metric))
      log.CreatedResource(args.metric_name)
      return result
    except apitools_base.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))

  def Display(self, unused_args, result):
    """This method is called to print the result of the Run() method.

    Args:
      unused_args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    list_printer.PrintResourceList('logging.metrics', [result])


Create.detailed_help = {
    'DESCRIPTION': """\
        Creates a logs-based metric to count the number of log entries that
        match a filter expression.
        When creating a metric, the description field can be empty but the
        filter expression must not be empty.
    """,
    'EXAMPLES': """\
        To create a metric that counts the number of log entries with a
        severity level higher than WARNING, run:

          $ {command} high_severity_count \\
            "Number of high severity log entries" \\
            "metadata.severity > WARNING"

        Detailed information about filters can be found at:
        https://cloud.google.com/logging/docs/view/advanced_filters
    """,
}
