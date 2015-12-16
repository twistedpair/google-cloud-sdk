# Copyright 2014 Google Inc. All Rights Reserved.

"""'logging sinks create' command."""

from googlecloudsdk.api_lib.logging import util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io
from googlecloudsdk.third_party.apitools.base.py import exceptions as apitools_exceptions


class Create(base.Command):
  """Creates a sink."""

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        'sink_name', help='The name for the sink.')
    parser.add_argument(
        'destination', help='The destination for the sink.')
    parser.add_argument(
        '--log-filter', required=False,
        help=('A filter expression for the sink. If present, the filter '
              'specifies which log entries to export.'))

  def CreateLogSink(self, sink_data):
    """Creates a log sink specified by the arguments."""
    client = self.context['logging_client_v1beta3']
    messages = self.context['logging_messages_v1beta3']
    sink_ref = self.context['sink_reference']
    return client.projects_logs_sinks.Create(
        messages.LoggingProjectsLogsSinksCreateRequest(
            projectsId=sink_ref.projectsId, logsId=sink_ref.logsId,
            logSink=messages.LogSink(**sink_data)))

  def CreateLogServiceSink(self, sink_data):
    """Creates a log service sink specified by the arguments."""
    client = self.context['logging_client_v1beta3']
    messages = self.context['logging_messages_v1beta3']
    sink_ref = self.context['sink_reference']
    return client.projects_logServices_sinks.Create(
        messages.LoggingProjectsLogServicesSinksCreateRequest(
            projectsId=sink_ref.projectsId,
            logServicesId=sink_ref.logServicesId,
            logSink=messages.LogSink(**sink_data)))

  def CreateProjectSink(self, sink_data):
    """Creates a project sink specified by the arguments."""
    client = self.context['logging_client_v1beta3']
    messages = self.context['logging_messages_v1beta3']
    sink_ref = self.context['sink_reference']
    return client.projects_sinks.Create(
        messages.LoggingProjectsSinksCreateRequest(
            projectsId=sink_ref.projectsId,
            logSink=messages.LogSink(**sink_data)))

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      The created sink with its destination.
    """
    if not (args.log or args.service or args.log_filter):
      # Attempt to create a project sink with an empty filter.
      if not console_io.PromptContinue(
          'Really create sink [%s] with an empty filter?' % args.sink_name):
        raise exceptions.ToolException('action canceled by user')

    sink_ref = self.context['sink_reference']
    sink_data = {'name': sink_ref.sinksId, 'destination': args.destination,
                 'filter': args.log_filter}

    try:
      if args.log:
        result = util.TypedLogSink(self.CreateLogSink(sink_data),
                                   log_name=args.log)
      elif args.service:
        result = util.TypedLogSink(self.CreateLogServiceSink(sink_data),
                                   service_name=args.service)
      else:
        result = util.TypedLogSink(self.CreateProjectSink(sink_data))
      log.CreatedResource(sink_ref)
      return result
    except apitools_exceptions.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))

  def Display(self, unused_args, result):
    """This method is called to print the result of the Run() method.

    Args:
      unused_args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    list_printer.PrintResourceList('logging.typedSinks', [result])
    util.PrintPermissionInstructions(result.destination)


Create.detailed_help = {
    'DESCRIPTION': """\
        Creates a sink used to export entries from one or more logs to
        a destination.
        A "log" sink exports a single log, specified by the *--log* flag.
        A "log service" sink exports all logs from a log service,
        specified by the *--log-service* flag.
        If you don't include one of the *--log* or *--log-service* flags,
        this command creates a project sink.
        A "project" sink exports all logs that matches *--log-filter* flag.
        An empty filter will match all logs.
        The sink's destination can be a Cloud Storage bucket,
        a BigQuery dataset, or a Cloud Pub/Sub topic.
        The destination must already exist and Cloud Logging must have
        permission to write to it.
        Log entries are exported as soon as the sink is created.
    """,
    'EXAMPLES': """\
        To export all Google App Engine logs to BigQuery, run:

          $ {command} --log-service=appengine.googleapis.com my-bq-sink \\
            bigquery.googleapis.com/projects/my-project/datasets/my_dataset

        To export "syslog" from App Engine Managed VM's to Cloud Storage, run:

          $ {command} --log=appengine.googleapis.com/syslog my-gcs-sink \\
            storage.googleapis.com/my-bucket

        To export Google App Engine logs with ERROR severity, run:

          $ {command} my-error-logs \\
            bigquery.googleapis.com/project/my-project/dataset/my_dataset \\
            --log-filter='metadata.serviceName="appengine.googleapis.com" AND metadata.severity=ERROR'

        Detailed information about filters can be found at:
        https://cloud.google.com/logging/docs/view/advanced_filters
    """,
}
