# Copyright 2013 Google Inc. All Rights Reserved.

"""The gcloud app get-logs command."""
from googlecloudsdk.api_lib.app import appengine_client
from googlecloudsdk.api_lib.app import flags
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions


class GetLogs(base.Command):
  """Gets the logs for the given module.

  This command gets the logs for the given module.  Logs will be downloaded to
  the file given as ``OUTPUT_FILE''.  If not provided, the logs will be printed
  to standard out.  You can append new logs to an existing downloaded log file
  by using the ``--append'' flag.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To download and print the last day's worth of request logs for a
          module, run:

            $ {command} mymodule --version=1

          By default, this will get only request logs (not application level
          logs).  To get your application level logs at a given severity level
          and higher, use the --severity flag:

            $ {command} mymodule --version=1 --severity=debug

          Logs can be saved to a file instead of being printed to standard out
          by specifying a file name:

            $ {command} mymodule --version=1 ~/log_file.txt

          You can append new logs to a previously downloaded log file by using
          --append mode:

            $ {command} mymodule --version=1 ~/log_file.txt --append

          To download all available logs (not just the last day's worth), run:

            $ {command} mymodule --version=1 ~/log_file.txt --days=0
          """,
  }

  SEVERITIES = ['debug', 'info', 'warning', 'error', 'critical']

  @staticmethod
  def Args(parser):
    """Get arguments for this command.

    Args:
      parser: argparse.ArgumentParser, the parser for this command.
    """
    flags.SERVER_FLAG.AddToParser(parser)
    flags.VERSION_FLAG.AddToParser(parser)
    parser.add_argument(
        'module',
        help='The module to get the logs for.')

    filters = parser.add_argument_group(
        'Log filters',
        'The following flags determine which log messages are returned.')
    filters.add_argument(
        '--severity',
        choices=GetLogs.SEVERITIES,
        help='The severity of app level logs to get.  If not given, only '
        'request logs are returned.')
    filters.add_argument(
        '--end-date',
        type=arg_parsers.Day.Parse,
        help='End date (as YYYY-MM-DD) of period for log data. Defaults to '
        'today.')
    filters.add_argument(
        '--days',
        type=int,
        help='The number of days worth of logs to get.  Use 0 for all '
        'available logs; default is 1 day.  This option cannot be used with '
        '--append mode.  Append mode will get all logs since logs were last '
        'retrieved.')
    filters.add_argument(
        '--vhost',
        help='Only return log messages from this virtual host.  Defaults to '
        'all virtual hosts.')

    includes = parser.add_argument_group(
        'Included fields',
        'The following flags determine which fields are returned in each log '
        'line.')
    includes.add_argument(
        '--details',
        action='store_true',
        default=None,
        help='Include all available data in each log line.')

    output = parser.add_argument_group(
        'Output options',
        'The following determine how the data is output.')
    output.add_argument(
        '--append',
        action='store_true',
        help='Append the logs to an existing file.')
    output.add_argument(
        'output_file',
        nargs='?',
        default='-',
        help='The file to write the logs to.  If "-" or if not given, logs are '
        'printed to standard out.')

  def Run(self, args):
    client = appengine_client.AppengineClient(args.server)
    severity = (GetLogs.SEVERITIES.index(args.severity)
                if args.severity else None)
    include_vhost = args.details
    include_all = args.details
    if args.append:
      if args.output_file == '-':
        raise exceptions.InvalidArgumentException(
            'OUTPUT_FILE', 'You must specify a file when using append mode')
      if args.days is not None:
        raise exceptions.InvalidArgumentException(
            '--days', 'You cannot use the --days flag when in append mode.  '
            'All logs will be fetched back to the last entry found in the '
            'output file.')
      client.GetLogsAppend(
          args.module, args.version, severity, args.vhost, include_vhost,
          include_all, args.end_date, args.output_file)
    else:
      client.GetLogs(
          args.module, args.version, severity, args.vhost, include_vhost,
          include_all, args.days, args.end_date, args.output_file)
