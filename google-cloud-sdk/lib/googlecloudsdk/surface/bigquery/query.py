# Copyright 2014 Google Inc. All Rights Reserved.

"""Implementation of gcloud bigquery query.
"""

from googlecloudsdk.api_lib.bigquery import job_control
from googlecloudsdk.api_lib.bigquery import job_ids
from googlecloudsdk.api_lib.bigquery import job_progress
from googlecloudsdk.api_lib.bigquery import message_conversions
from googlecloudsdk.api_lib.bigquery import schema_and_rows
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.surface import bigquery as commands


class Query(base.Command):
  """Executes an SQL query.

  A table or view reference in the query has the form
      dataset_name/table_or_view_name
  (for a dataset in the current project) or
      /project_name/dataset_name/table_or_view_name
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        '--allow-large-results',
        action='store_true',
        help='Enable larger --append-to or --write-to table sizes.')
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument(
        '--append-to',
        help='Name of a table to which query results will be appended.')
    output_group.add_argument(
        '--write-to',
        help='Name of a table to which query results will be written '
        '(replacing the old contents of the table, if any).')
    parser.add_argument(
        '--async',
        action='store_true',
        help='Create an asynchronous job to perform the query.')
    parser.add_argument(
        '--batch', action='store_true', help='Run the query in batch mode.')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate the query, but do not execute it.')
    parser.add_argument(
        '--job-id', help='A unique job ID to use for the request.')
    parser.add_argument(
        '--limit',
        type=int,
        default=100,
        help='How many rows to return in the result.')
    parser.add_argument(
        '--require-cache',
        action='store_true',
        help='Run the query only if it is already cached.')
    parser.add_argument(
        '--start-row',
        type=int,
        default=0,
        help='First row to return in the result.')
    parser.add_argument(
        '--status',
        choices=[
            job_progress.STATUS_REPORTING_PERIODIC,
            job_progress.STATUS_REPORTING_CHANGES,
            job_progress.STATUS_REPORTING_NONE],
        default=job_progress.STATUS_REPORTING_PERIODIC,
        help='Whether the status of the query job should be reported '
        'periodically, every time the status changes, or not at all.')
    parser.add_argument(
        '--structured',
        action='store_true',
        help='Preserve nested and repeated fields in the result schema. '
        'If not set, rows in the result are flattened.')
    parser.add_argument(
        '--use-cache',
        action='store_true',
        help='Use the query cache to avoid rerunning cached queries.')
    parser.add_argument(
        'sql_query',
        help='an SQL SELECT statement (typically in the form of a quoted '
        'string)')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace, All the arguments that were provided to this
        command invocation.

    Raises:
       ToolException: if no query was provided.

    Returns:
      If the --dry_run or --async flag was specified, None; otherwise, a
      SchemaAndRows object.
    """
    apitools_client = self.context[commands.APITOOLS_CLIENT_KEY]
    bigquery_messages = self.context[commands.BIGQUERY_MESSAGES_MODULE_KEY]
    resource_parser = self.context[commands.BIGQUERY_REGISTRY_KEY]
    project_id = properties.VALUES.core.project.Get(required=True)
    if not args.sql_query:
      raise exceptions.ToolException('No query string provided')
    destination_table = args.append_to or args.write_to
    if destination_table:
      output_resource = resource_parser.Parse(
          destination_table, collection='bigquery.tables')
      output_reference = message_conversions.TableResourceToReference(
          bigquery_messages, output_resource)
    else:
      output_reference = None
    query_configuration = bigquery_messages.JobConfigurationQuery(
        allowLargeResults=args.allow_large_results,
        createDisposition='CREATE_NEVER' if args.require_cache else None,
        # Set defaultDataset here if we choose to support a
        # --default-dataset-in-query flag.
        destinationTable=output_reference,
        flattenResults=not args.structured,
        preserveNulls=None,
        priority='BATCH' if args.batch else None,
        query=args.sql_query,
        useQueryCache=args.use_cache,
        writeDisposition=(
            (args.append_to and 'WRITE_APPEND')
            or (args.write_to and 'WRITE_TRUNCATE')))
    job = job_control.ExecuteJob(
        apitools_client,
        bigquery_messages,
        args,
        configuration=bigquery_messages.JobConfiguration(
            query=query_configuration, dryRun=args.dry_run),
        async=args.async,
        project_id=project_id,
        job_id=job_ids.JobIdProvider().GetJobId(
            args.job_id, args.fingerprint_job_id))

    if args.dry_run:
      log.Print(
          'Query successfully validated. Assuming the tables are not '
          'modified, running this query will process {0} bytes of data.'
          .format(job.statistics.query.totalBytesProcessed))
      return None
    if args.async:
      job_resource = resource_parser.Create(
          'bigquery.jobs',
          projectId=job.jobReference.projectId,
          jobId=job.jobReference.jobId)
      log.CreatedResource(job_resource)
      self.default_format = 'table(jobId, projectId)'
      return job_resource
    result = schema_and_rows.GetJobSchemaAndRows(
        apitools_client, bigquery_messages, job.jobReference, args.start_row,
        args.limit)
    if not result:
      return None
    self.default_format = result.GetDefaultFormat()
    return result.PrepareForDisplay()

  def Format(self, args):
    """Returns the default format string.

    Args:
      args: The arguments that command was run with.

    Returns:
      The default format string.
    """
    return self.default_format
