# Copyright 2014 Google Inc. All Rights Reserved.

"""'logging sinks update' command."""

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import log
from googlecloudsdk.third_party.apitools.base import py as apitools_base

from googlecloudsdk.logging.lib import util


class Update(base.Command):
  """Updates a sink."""

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        'sink_name', help='The name of the sink to update.')
    parser.add_argument(
        'destination', nargs='?',
        help=('A new destination for the sink. '
              'If omitted, the sink\'s existing destination is unchanged.'))
    parser.add_argument(
        '--log-filter', required=False,
        help=('A new filter expression for the sink. '
              'If omitted, the sink\'s existing filter (if any) is unchanged.'))

  def GetLogSink(self):
    """Returns a log sink specified by the arguments."""
    client = self.context['logging_client']
    return client.projects_logs_sinks.Get(
        self.context['sink_reference'].Request())

  def GetLogServiceSink(self):
    """Returns a log service sink specified by the arguments."""
    client = self.context['logging_client']
    return client.projects_logServices_sinks.Get(
        self.context['sink_reference'].Request())

  def GetProjectSink(self):
    """Returns a project sink specified by the arguments."""
    client = self.context['logging_client']
    return client.projects_sinks.Get(
        self.context['sink_reference'].Request())

  def UpdateLogSink(self, sink):
    """Updates a log sink specified by the arguments."""
    client = self.context['logging_client']
    messages = self.context['logging_messages']
    sink_ref = self.context['sink_reference']
    return client.projects_logs_sinks.Update(
        messages.LoggingProjectsLogsSinksUpdateRequest(
            projectsId=sink_ref.projectsId, logsId=sink_ref.logsId,
            sinksId=sink.name, logSink=sink))

  def UpdateLogServiceSink(self, sink):
    """Updates a log service sink specified by the arguments."""
    client = self.context['logging_client']
    messages = self.context['logging_messages']
    sink_ref = self.context['sink_reference']
    return client.projects_logServices_sinks.Update(
        messages.LoggingProjectsLogServicesSinksUpdateRequest(
            projectsId=sink_ref.projectsId,
            logServicesId=sink_ref.logServicesId, sinksId=sink.name,
            logSink=sink))

  def UpdateProjectSink(self, sink):
    """Updates a project sink specified by the arguments."""
    client = self.context['logging_client']
    messages = self.context['logging_messages']
    sink_ref = self.context['sink_reference']
    return client.projects_sinks.Update(
        messages.LoggingProjectsSinksUpdateRequest(
            projectsId=sink_ref.projectsId, sinksId=sink.name, logSink=sink))

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      The updated sink with its new destination.
    """
    # One of the flags is required to update the sink.
    # log_filter can be an empty string, so check explicitly for None.
    if not args.destination and args.log_filter is None:
      raise exceptions.ToolException(
          '[destination] or --log-filter argument is required')

    # Calling Update on a non-existing sink creates it.
    # We need to make sure it exists, otherwise we would create it.
    try:
      if args.log:
        sink = self.GetLogSink()
      elif args.service:
        sink = self.GetLogServiceSink()
      else:
        sink = self.GetProjectSink()
    except apitools_base.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))

    # Only update fields that were passed to the command.
    if args.destination:
      destination = args.destination
    else:
      destination = sink.destination

    if args.log_filter is not None:
      log_filter = args.log_filter
    else:
      log_filter = sink.filter

    sink_ref = self.context['sink_reference']
    updated_sink = self.context['logging_messages'].LogSink(
        name=sink_ref.sinksId, destination=destination, filter=log_filter)

    try:
      if args.log:
        result = self.UpdateLogSink(updated_sink)
      elif args.service:
        result = self.UpdateLogServiceSink(updated_sink)
      else:
        result = self.UpdateProjectSink(updated_sink)
      log.UpdatedResource(sink_ref)
      return result
    except apitools_base.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))

  def Display(self, unused_args, result):
    """This method is called to print the result of the Run() method.

    Args:
      unused_args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    list_printer.PrintResourceList('logging.sinks', [result])
    util.PrintPermissionInstructions(result.destination)


Update.detailed_help = {
    'DESCRIPTION': """\
        Changes the *[destination]* or *--log-filter* associated with a sink.
        If you don't include one of the *--log* or *--log-service* flags,
        this command updates a project sink.
        The new destination must already exist and Cloud Logging must have
        permission to write to it.
        Log entries are exported to the new destination immediately.
    """,
    'EXAMPLES': """\
        To only update a project sink filter, run:

          $ {command} my-sink --log-filter='metadata.severity>=ERROR'

        Detailed information about filters can be found at:
        https://cloud.google.com/logging/docs/view/advanced_filters
   """,
}
