# Copyright 2015 Google Inc. All Rights Reserved.

"""'functions get-logs' command."""

from googlecloudsdk.api_lib.functions import util
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.util import attrpath


class GetLogs(base.Command):
  """Show logs produced by functions.

  This command displays log entries produced by a all functions running in a
  region, or by a single function if it is specified through a command argument.
  By default, when no extra flags are specified, the most recent 20 log entries
  are displayed.
  """

  SEVERITIES = ['DEBUG', 'INFO', 'ERROR']

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        'name', nargs='?',
        help=('Name of the function which logs are to be displayed. If no name '
              'is specified, logs from all functions are displayed.'))
    parser.add_argument(
        '--execution-id',
        help=('Execution ID for which logs are to be displayed.'))
    parser.add_argument(
        '--start-time', required=False, type=arg_parsers.Datetime.Parse,
        help=('Return only log entries which timestamps are not earlier than '
              'the specified time. The timestamp must be in RFC3339 UTC "Zulu" '
              'format. If --start-time is specified, the command returns '
              '--limit earliest log entries which appeared after '
              '--start-time.'))
    parser.add_argument(
        '--end-time', required=False, type=arg_parsers.Datetime.Parse,
        help=('Return only log entries which timestamps are not later than '
              'the specified time. The timestamp must be in RFC3339 UTC "Zulu" '
              'format. If --end-time is specified but --start-time is not, the '
              'command returns --limit latest log entries which appeared '
              'before --end-time.'))
    parser.add_argument(
        '--limit', required=False, type=arg_parsers.BoundedInt(1, 1000),
        default=20,
        help=('Number of log entries to be fetched; must not be greater than '
              '1000.'))
    parser.add_argument(
        '--min-log-level', choices=GetLogs.SEVERITIES,
        help=('Minimum level of logs to be fetched; can be one of DEBUG, INFO, '
              'ERROR.'))
    parser.add_argument(
        '--show-log-levels', action='store_true', default=True,
        help=('Print a log level of each log entry.'))
    parser.add_argument(
        '--show-function-names', action='store_true', default=True,
        help=('Print a function name before each log entry.'))
    parser.add_argument(
        '--show-execution-ids', action='store_true', default=True,
        help=('Print an execution ID before each log entry.'))
    parser.add_argument(
        '--show-timestamps', action='store_true', default=True,
        help=('Print a UTC timestamp before each log entry.'))

  @util.CatchHTTPErrorRaiseHTTPException
  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Yields:
      Objects representing log entries.
    """
    logging_client = self.context['logging_client']
    logging = self.context['logging_messages']

    project = properties.VALUES.core.project.Get(required=True)

    log_filter = (
        'resource.type="cloud_function" '
        'labels."cloudfunctions.googleapis.com/region"="{0}" '
        .format(args.region))
    if args.name:
      log_filter += (
          'labels."cloudfunctions.googleapis.com/function_name"="{0}" '
          .format(args.name))
    if args.execution_id:
      log_filter += 'labels."execution_id"="{0}" '.format(args.execution_id)
    if args.min_log_level:
      log_filter += 'severity>={0} '.format(args.min_log_level)
    if args.start_time:
      order = 'asc'
      start_time = args.start_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
      log_filter += 'timestamp>="{0}" '.format(start_time)
    else:
      order = 'desc'
    if args.end_time:
      end_time = args.end_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
      log_filter += 'timestamp<="{0}" '.format(end_time)
    # TODO(swalk): Consider using paging for listing more than 1000 log entries.
    # However, reversing the order of received latest N entries before a
    # specified timestamp would be problematic with paging.
    request = logging.ListLogEntriesRequest(
        projectIds=[project], filter=log_filter,
        orderBy='timestamp {0}'.format(order), pageSize=args.limit)
    response = logging_client.entries.List(request=request)

    entries = response.entries if order == 'asc' else reversed(response.entries)
    for entry in entries:
      row = dict(
          log=entry.textPayload
      )
      if entry.severity:
        severity = str(entry.severity)
        if severity in GetLogs.SEVERITIES:
          # Use short form (first letter) for expected severities.
          row['level'] = severity[0]
        else:
          # Print full form of unexpected severities.
          row['level'] = severity
      for label in entry.labels.additionalProperties:
        if label.key == 'cloudfunctions.googleapis.com/function_name':
          row['name'] = label.value
        if label.key == 'execution_id':
          row['execution_id'] = label.value
      if entry.timestamp:
        row['time_utc'] = util.FormatTimestamp(entry.timestamp)
      yield row

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    columns = []
    if args.show_log_levels:
      columns.append(('LEVEL', attrpath.Selector('level')))
    if args.show_function_names:
      columns.append(('NAME', attrpath.Selector('name')))
    if args.show_execution_ids:
      columns.append(('EXECUTION_ID', attrpath.Selector('execution_id')))
    if args.show_timestamps:
      columns.append(('TIME_UTC', attrpath.Selector('time_utc')))
    columns.append(('LOG', attrpath.Selector('log')))

    console_io.PrintExtendedList(result, columns)
