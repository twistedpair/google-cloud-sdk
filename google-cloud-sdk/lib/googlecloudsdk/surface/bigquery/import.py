# Copyright 2014 Google Inc. All Rights Reserved.

"""Implementation of gcloud bigquery import.
"""

import os
from googlecloudsdk.api_lib.bigquery import bigquery_client_helper
from googlecloudsdk.api_lib.bigquery import bigquery_schemas
from googlecloudsdk.api_lib.bigquery import job_control
from googlecloudsdk.api_lib.bigquery import job_ids
from googlecloudsdk.api_lib.bigquery import job_progress
from googlecloudsdk.api_lib.bigquery import message_conversions
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.surface import bigquery as commands


class Import(base.Command):
  """Import data from a specified source into a specified destination table.

  If the table does not exist, it is created. Otherwise, the imported data is
  added to the table.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To import data from csv with given schema specified in json file, run:

            $ {command} ds/new_tbl ./info.csv --schema ./info_schema.json

          To import data located on cloud storage, run:

            $ {command} ds/new_tbl gs://mybucket/info.csv --schema-file ./info_schema.json

          To import data with command line specified schema, run:

            $ {command} ds/small gs://mybucket/small.csv --schema name:integer,value:string

          To import data with default field string type, run:

            $ {command} ds/small gs://mybucket/small.csv --schema field1,field2,field3
       """,
  }

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        '--allow-jagged-rows',
        action='store_true',
        help='Allow missing trailing optional columns in CSV import data.')
    parser.add_argument(
        '--allow-quoted-newlines',
        action='store_true',
        help='Allow quoted newlines in CSV import data.')
    parser.add_argument(
        '--async',
        action='store_true',
        help='Create an asynchronous job to perform the import.')
    parser.add_argument(
        '--encoding',
        choices=['iso-8859-1', 'utf-8'],
        default='utf-8',
        help='The character encoding used for the source data.')
    parser.add_argument(
        '--field-delimiter',
        default=',',
        help='The character that indicates the boundary between columns in '
        'CSV source data. "\t" and "tab" are accepted names for tab.')
    parser.add_argument(
        '--ignore-unknown-values',
        action='store_true',
        help='Allow and ignore extra, unrecognized values in CSV or JSON '
        'import data.')
    parser.add_argument(
        '--job-id',
        help='A unique job_id to use for the request. If this flag is not '
        'specified, a job_id will be generated automatically and displayed as '
        'the result of the command.')
    parser.add_argument(
        '--max-bad-records',
        type=int,
        default=0,
        help='Maximum number of bad records allowed before the entire job '
        'fails.')
    parser.add_argument(
        '--quote',
        default='"',
        help='Quote character to use to enclose records. Default is the '
        'double-quote character ("). To indicate no quote character at all, '
        'use an empty string.')
    parser.add_argument(
        '--replace',
        action='store_true',
        help='Erase existing contents before loading new data.')
    parser.add_argument(
        '--schema',
        help='A comma-separated list of entries of the form name[:type], where '
        'type defaults to string if not present, specifying field names and '
        'types for the destination table. Possible types are string, integer, '
        'float, boolean, record, and timestamp.')
    parser.add_argument(
        '--schema-file',
        help='The name of a JSON file containing a single array object, each '
        'element of which is an object with properties name, type, and, '
        'optionally, mode, specifying a schema for the destination table. '
        'Possible types are string, integer, float, boolean, record, and '
        'timestamp.  Possible modes are NULLABLE, REQUIRED, and REPEATED.')
    parser.add_argument(
        '--skip-leading-rows',
        type=int,
        default=0,
        help='The number of rows at the beginning of the source data to skip.')
    parser.add_argument(
        '--source-format',
        choices=['csv', 'newline-delimited-json', 'datastore-backup'],
        help='Format of source data.')
    parser.add_argument(
        '--status',
        choices=[
            job_progress.STATUS_REPORTING_PERIODIC,
            job_progress.STATUS_REPORTING_CHANGES,
            job_progress.STATUS_REPORTING_NONE],
        default=job_progress.STATUS_REPORTING_PERIODIC,
        help='Whether the status of the import job should be reported '
        'periodically, every time the status changes, or not at all.')
    parser.add_argument(
        'source',
        help=' Either a path to a single local file containing CSV or JSON '
        'data, or a comma-separated list of URIs with the protocol gs:, '
        'specifying files in Google Storage.')
    parser.add_argument(
        'destination_table',
        help='The fully-qualified name of table into which data is to be '
        'imported.')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace, All the arguments that were provided to this
        command invocation.

    Returns:

    """
    apitools_client = self.context[commands.APITOOLS_CLIENT_KEY]
    bigquery_messages = self.context[commands.BIGQUERY_MESSAGES_MODULE_KEY]
    resource_parser = self.context[commands.BIGQUERY_REGISTRY_KEY]
    project_id = properties.VALUES.core.project.Get(required=True)
    table_resource = resource_parser.Parse(
        args.destination_table, collection='bigquery.tables')
    # TODO(nhcohen): Define constants for collection names in one place
    table_reference = message_conversions.TableResourceToReference(
        bigquery_messages, table_resource)

    sources = _ProcessSources(args.source)

    if args.schema:
      table_schema = bigquery_schemas.ReadSchema(args.schema, bigquery_messages)
    elif args.schema_file:
      table_schema = bigquery_schemas.ReadSchemaFile(
          args.schema_file, bigquery_messages)
    else:
      table_schema = None

    normalized_source_format = bigquery_client_helper.NormalizeTextualFormat(
        args.source_format)

    if (not normalized_source_format) or normalized_source_format == 'CSV':
      normalized_quote = (
          args.quote
          and bigquery_client_helper.NormalizeFieldDelimiter(args.quote))
      normalized_skip_leading_rows = args.skip_leading_rows
    else:
      # Server accepts non-None quote and skipLeadingRows only for CSV source
      # format:
      normalized_quote = None
      normalized_skip_leading_rows = None

    load_config = bigquery_messages.JobConfigurationLoad(
        allowJaggedRows=args.allow_jagged_rows,
        allowQuotedNewlines=args.allow_quoted_newlines,
        destinationTable=table_reference,
        encoding=args.encoding and args.encoding.upper(),
        fieldDelimiter=(
            args.field_delimiter
            and bigquery_client_helper.NormalizeFieldDelimiter(
                args.field_delimiter)),
        ignoreUnknownValues=args.ignore_unknown_values,
        maxBadRecords=args.max_bad_records,
        quote=normalized_quote,
        schema=table_schema,
        skipLeadingRows=normalized_skip_leading_rows,
        sourceFormat=normalized_source_format,
        sourceUris=sources if sources[0].startswith('gs://') else [],
        writeDisposition='WRITE_TRUNCATE' if args.replace else None,
    )
    job = job_control.ExecuteJob(
        apitools_client,
        bigquery_messages,
        args,
        configuration=bigquery_messages.JobConfiguration(load=load_config),
        async=args.async,
        project_id=project_id,
        upload_file=None if sources[0].startswith('gs://') else sources[0],
        job_id=job_ids.JobIdProvider().GetJobId(
            args.job_id, args.fingerprint_job_id))
    if args.async:
      job_resource = resource_parser.Create(
          'bigquery.jobs',
          projectId=job.jobReference.projectId,
          jobId=job.jobReference.jobId)
      log.CreatedResource(job_resource)

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    pass


def _ProcessSources(source_string):
  """Take a source string and return a list of URIs.

  The list will consist of either a single local filename, which
  we check exists and is a file, or a list of gs:// uris.

  Args:
    source_string: A comma-separated list of URIs.

  Returns:
    List of one or more valid URIs, as strings.

  Raises:
    BigqueryClientError: if no valid list of sources can be determined.
    ToolException: if source_string is empty or have no storage uris.
  """
  # TODO(nhcohen): Consider whether we can use googlecloudsdk.core.resources
  sources = [source.strip() for source in source_string.split(',')]
  gs_uris = [source for source in sources if source.startswith('gs://')]
  if not sources:
    raise exceptions.ToolException('No sources specified')
  if gs_uris:
    if len(gs_uris) != len(sources):
      raise exceptions.ToolException(
          'All URIs must begin with "gs://" if any do.')
    return sources
  else:
    source = sources[0]
    if len(sources) > 1:
      raise exceptions.ToolException(
          'Local upload currently supports only one file, found {0}'.format(
              len(sources)))
    if not os.path.isfile(source):
      if os.path.exists(source):
        raise exceptions.ToolException(
            'Source path is not a file: {0}'.format(source))
      else:
        raise exceptions.ToolException(
            'Source file not found: {0}'.format(source))
  return sources
