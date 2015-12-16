# Copyright 2014 Google Inc. All Rights Reserved.

"""'logging sinks list' command."""

from googlecloudsdk.api_lib.logging import util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import properties
from googlecloudsdk.third_party.apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.third_party.apitools.base.py import list_pager


class List(base.Command):
  """Lists the defined sinks."""

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        '--only-project-sinks', required=False, action='store_true',
        help='Display only project sinks.')
    parser.add_argument(
        '--limit', required=False, type=int, default=None,
        help='If greater than zero, limit the number of results.')

  def ListLogSinks(self, project, log_name, limit):
    """List log sinks from the specified log."""
    client = self.context['logging_client_v1beta3']
    messages = self.context['logging_messages_v1beta3']
    result = client.projects_logs_sinks.List(
        messages.LoggingProjectsLogsSinksListRequest(
            projectsId=project, logsId=log_name))
    for sink in result.sinks:
      yield util.TypedLogSink(sink, log_name=log_name)
      limit -= 1
      if not limit:
        return

  def ListLogServiceSinks(self, project, service_name, limit):
    """List log service sinks from the specified service."""
    client = self.context['logging_client_v1beta3']
    messages = self.context['logging_messages_v1beta3']
    result = client.projects_logServices_sinks.List(
        messages.LoggingProjectsLogServicesSinksListRequest(
            projectsId=project, logServicesId=service_name))
    for sink in result.sinks:
      yield util.TypedLogSink(sink, service_name=service_name)
      limit -= 1
      if not limit:
        return

  def ListProjectSinks(self, project, limit):
    """List project sinks from the specified project."""
    client = self.context['logging_client_v1beta3']
    messages = self.context['logging_messages_v1beta3']
    result = client.projects_sinks.List(
        messages.LoggingProjectsSinksListRequest(projectsId=project))
    for sink in result.sinks:
      yield util.TypedLogSink(sink)
      limit -= 1
      if not limit:
        return

  def YieldAllSinks(self, project, limit):
    """Yield all log and log service sinks from the specified project."""
    client = self.context['logging_client_v1beta3']
    messages = self.context['logging_messages_v1beta3']
    # First get all the log sinks.
    response = list_pager.YieldFromList(
        client.projects_logs,
        messages.LoggingProjectsLogsListRequest(projectsId=project),
        field='logs', batch_size=None, batch_size_attribute='pageSize')
    for log in response:
      # We need only the base log name, not the full resource uri.
      log_name = util.ExtractLogName(log.name)
      for typed_sink in self.ListLogSinks(project, log_name, limit):
        yield typed_sink
        limit -= 1
        if not limit:
          return
    # Now get all the log service sinks.
    response = list_pager.YieldFromList(
        client.projects_logServices,
        messages.LoggingProjectsLogServicesListRequest(projectsId=project),
        field='logServices', batch_size=None, batch_size_attribute='pageSize')
    for service in response:
      # In contrast, service.name correctly contains only the name.
      for typed_sink in self.ListLogServiceSinks(project, service.name, limit):
        yield typed_sink
        limit -= 1
        if not limit:
          return
    # Lastly, get all project sinks.
    for typed_sink in self.ListProjectSinks(project, limit):
      yield typed_sink
      limit -= 1
      if not limit:
        return

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      The list of sinks.
    """
    project = properties.VALUES.core.project.Get(required=True)

    if args.limit is None or args.limit <= 0:
      limit = float('inf')
    else:
      limit = args.limit

    try:
      if args.log:
        return self.ListLogSinks(project, args.log, limit)
      elif args.service:
        return self.ListLogServiceSinks(project, args.service, limit)
      elif args.only_project_sinks:
        return self.ListProjectSinks(project, limit)
      else:
        return self.YieldAllSinks(project, limit)
    except apitools_exceptions.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    list_printer.PrintResourceList('logging.typedSinks', result)


List.detailed_help = {
    'DESCRIPTION': """\
        {index}
        If either the *--log* or *--log-service* flags are included, then
        the only sinks listed are for that log or that service.
        If *--only-project-sinks* flag is included, then only project sinks
        are listed.
        If none of the flags are included, then all sinks in use are listed.
    """,
}
