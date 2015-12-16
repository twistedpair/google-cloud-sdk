# Copyright 2015 Google Inc. All Rights Reserved.

"""'logging metrics update' command."""

from googlecloudsdk.api_lib.logging import util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.third_party.apitools.base.py import exceptions as apitools_exceptions


class Update(base.Command):
  """Updates the definition of a logs-based metric."""

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        'metric_name', help='The name of the log-based metric to update.')
    parser.add_argument(
        '--description', required=False,
        help=('A new description for the metric. '
              'If omitted, the description is not changed.'))
    parser.add_argument(
        '--filter', required=False,
        help=('A new filter string for the metric. '
              'If omitted, the filter is not changed.'))

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to
        this command invocation.

    Returns:
      The updated metric.
    """
    # One of the flags is required to update the metric.
    if not (args.description or args.filter):
      raise exceptions.ToolException(
          '--description or --filter argument is required')

    client = self.context['logging_client_v1beta3']
    messages = self.context['logging_messages_v1beta3']
    project = properties.VALUES.core.project.Get(required=True)
    # Calling the API's Update method on a non-existing metric creates it.
    # Make sure the metric exists so we don't accidentally create it.
    try:
      metric = client.projects_metrics.Get(
          messages.LoggingProjectsMetricsGetRequest(
              metricsId=args.metric_name,
              projectsId=project))
    except apitools_exceptions.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))

    if args.description:
      metric_description = args.description
    else:
      metric_description = metric.description
    if args.filter:
      metric_filter = args.filter
      # This prevents a clash with the Cloud SDK --filter flag.
      args.filter = None
    else:
      metric_filter = metric.filter

    updated_metric = messages.LogMetric(
        name=args.metric_name,
        description=metric_description,
        filter=metric_filter)
    try:
      result = client.projects_metrics.Update(
          messages.LoggingProjectsMetricsUpdateRequest(
              logMetric=updated_metric,
              metricsId=args.metric_name,
              projectsId=project))
      log.UpdatedResource(args.metric_name)
      return result
    except apitools_exceptions.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))

  def Display(self, unused_args, result):
    """This method is called to print the result of the Run() method.

    Args:
      unused_args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    list_printer.PrintResourceList('logging.metrics', [result])


Update.detailed_help = {
    'DESCRIPTION': """\
        Updates the description or the filter expression of an existing
        logs-based metric.
    """,
    'EXAMPLES': """\
        To update the description of a metric called high_severity_count, run:

          $ {command} high_severity_count \\
            --description="Count of high-severity log entries."

        To update the filter expression of the metric, run:

          $ {command} high_severity_count \\
            --filter="metadata.severity >= WARNING"

        Detailed information about filters can be found at:
        https://cloud.google.com/logging/docs/view/advanced_filters
    """,
}
