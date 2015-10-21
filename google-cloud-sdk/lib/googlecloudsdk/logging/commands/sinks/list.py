# Copyright 2014 Google Inc. All Rights Reserved.

"""'logging sinks list' command."""

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import log as sdk_log
from googlecloudsdk.core import properties
from googlecloudsdk.third_party.apitools.base import py as apitools_base
from googlecloudsdk.third_party.apitools.base.py import list_pager

from googlecloudsdk.logging.lib import util


class List(base.Command):
  """Lists the defined sinks."""

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        '--only-project-sinks', required=False, action='store_true',
        help='Display only project sinks.')
    parser.add_argument(
        '--limit', required=False, type=int, default=0,
        help='If greater than zero, limit the number of results.')

  def ListLogSinks(self, project, log_name):
    """List log sinks from the specified log."""
    client = self.context['logging_client']
    messages = self.context['logging_messages']
    return client.projects_logs_sinks.List(
        messages.LoggingProjectsLogsSinksListRequest(
            projectsId=project, logsId=log_name))

  def ListLogServiceSinks(self, project, service_name):
    """List log service sinks from the specified service."""
    client = self.context['logging_client']
    messages = self.context['logging_messages']
    return client.projects_logServices_sinks.List(
        messages.LoggingProjectsLogServicesSinksListRequest(
            projectsId=project, logServicesId=service_name))

  def ListProjectSinks(self, project):
    """List project sinks from the specified project."""
    client = self.context['logging_client']
    messages = self.context['logging_messages']
    return client.projects_sinks.List(
        messages.LoggingProjectsSinksListRequest(projectsId=project))

  def CreateTypedSink(self, sink, sink_type, origin_name):
    """Create a sink representation that includes its origin."""
    return {'name': sink.name, 'destination': sink.destination,
            'type': '%s sink: %s' % (sink_type, origin_name)}

  def YieldAllSinks(self, project, limit):
    """Yield all log and log service sinks from the specified project."""
    client = self.context['logging_client']
    messages = self.context['logging_messages']
    remaining = limit if limit > 0 else float('inf')
    # Keep track if any description was truncated.
    self._truncated = False
    # First get all the log sinks.
    response = list_pager.YieldFromList(
        client.projects_logs,
        messages.LoggingProjectsLogsListRequest(projectsId=project),
        field='logs', batch_size=None, batch_size_attribute='pageSize')
    for log in response:
      # We need only the base log name, not the full resource uri.
      log_name = util.ExtractLogName(log.name)
      results = self.ListLogSinks(project, log_name)
      for sink in results.sinks:
        yield self.CreateTypedSink(sink, 'log', log_name)
        remaining -= 1
        if not remaining:
          return
    # Now get all the log service sinks.
    response = list_pager.YieldFromList(
        client.projects_logServices,
        messages.LoggingProjectsLogServicesListRequest(projectsId=project),
        field='logServices', batch_size=None, batch_size_attribute='pageSize')
    for service in response:
      # In contrast, service.name correctly contains only the name.
      results = self.ListLogServiceSinks(project, service.name)
      for sink in results.sinks:
        yield self.CreateTypedSink(sink, 'log-service', service.name)
        remaining -= 1
        if not remaining:
          return
    # Lastly, get all project sinks.
    results = self.ListProjectSinks(project)
    for sink in results.sinks:
      # Filters can be very long, display only a part of it.
      if not sink.filter:
        desc = '(empty filter)'
      elif len(sink.filter) > 50:
        if not self._truncated:
          self._truncated = True
        desc = sink.filter[:50] + '..'
      else:
        desc = sink.filter
      yield self.CreateTypedSink(sink, 'project', desc)
      remaining -= 1
      if not remaining:
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

    try:
      if args.log:
        results = self.ListLogSinks(project, args.log)
      elif args.service:
        results = self.ListLogServiceSinks(project, args.service)
      elif args.only_project_sinks:
        results = self.ListProjectSinks(project)
      else:
        return self.YieldAllSinks(project, args.limit)
      if args.limit > 0:
        return results.sinks[:args.limit]
      else:
        return list(results.sinks)
    except apitools_base.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    if not (args.log or args.service or args.only_project_sinks):
      list_printer.PrintResourceList('logging.typedSinks', result)
      if self._truncated:
        sdk_log.Print(('Some entries were truncated. '
                       'Use "logging sinks describe" for full details.'))
    else:
      list_printer.PrintResourceList('logging.sinks', result)


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
