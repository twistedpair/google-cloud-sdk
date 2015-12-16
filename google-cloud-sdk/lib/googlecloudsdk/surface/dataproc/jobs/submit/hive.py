# Copyright 2015 Google Inc. All Rights Reserved.

"""Submit a Hive job to a cluster."""

from googlecloudsdk.api_lib.dataproc import base_classes
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.third_party.apitools.base.py import encoding


class Hive(base_classes.JobSubmitter):
  """Submit a Hive job to a cluster."""

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To submit a Hive job with a local script, run:

            $ {command} --cluster my_cluster --file my_queries.q

          To submit a Hive job with inline queries, run:

            $ {command} --cluster my_cluster \\
                -e "CREATE EXTERNAL TABLE foo(bar int) LOCATION \
'gs://my_bucket/'" \\
                -e "SELECT * FROM foo WHERE bar > 2"
          """,
  }

  @staticmethod
  def Args(parser):
    super(Hive, Hive).Args(parser)
    parser.add_argument(
        '--execute', '-e',
        metavar='QUERY',
        dest='queries',
        action='append',
        default=[],
        help='A Hive query to execute as part of the job.')
    parser.add_argument(
        '--file', '-f',
        help='HCFS URI of file containing Hive script to execute as the job.')
    parser.add_argument(
        '--jars',
        type=arg_parsers.ArgList(),
        metavar='JAR',
        default=[],
        help=('Comma separated list of jar files to be provided to the '
              'Hive and MR. May contain UDFs.'))
    parser.add_argument(
        '--params',
        type=arg_parsers.ArgDict(),
        metavar='PARAM=VALUE',
        help='A list of key value pairs to set variables in the Hive queries.')
    parser.add_argument(
        '--properties',
        type=arg_parsers.ArgDict(),
        metavar='PROPERTY=VALUE',
        help='A list of key value pairs to configure Hive.')
    parser.add_argument(
        '--continue-on-failure',
        action='store_true',
        help='Whether to continue if a single query fails.')

  def PopulateFilesByType(self, args):
    # TODO(pclay): Replace with argument group.
    if not args.queries and not args.file:
      raise ValueError('Must either specify --execute or --file.')
    if args.queries and args.file:
      raise ValueError('Cannot specify both --execute and --file.')

    self.files_by_type.update({
        'jars': args.jars,
        'file': args.file})

  def ConfigureJob(self, job, args):
    messages = self.context['dataproc_messages']

    hive_job = messages.HiveJob(
        continueOnFailure=args.continue_on_failure,
        jarFileUris=self.files_by_type['jars'],
        queryFileUri=self.files_by_type['file'])

    if args.queries:
      hive_job.queryList = messages.QueryList(queries=args.queries)
    if args.params:
      hive_job.scriptVariables = encoding.DictToMessage(
          args.params, messages.HiveJob.ScriptVariablesValue)
    if args.properties:
      hive_job.properties = encoding.DictToMessage(
          args.properties, messages.HiveJob.PropertiesValue)

    job.hiveJob = hive_job
