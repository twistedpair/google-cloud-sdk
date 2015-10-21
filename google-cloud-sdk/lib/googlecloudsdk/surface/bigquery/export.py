# Copyright 2014 Google Inc. All Rights Reserved.

"""Implementation of gcloud bigquery export.
"""

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.shared.bigquery import bigquery_client_helper
from googlecloudsdk.shared.bigquery import job_control
from googlecloudsdk.shared.bigquery import job_ids
from googlecloudsdk.shared.bigquery import job_progress
from googlecloudsdk.shared.bigquery import message_conversions
from googlecloudsdk.surface import bigquery as commands


class Export(base.Command):
  """Exports data from a specified source table to one or more destinations.

  The data is exported in either CSV or newline-delimited-JSON format.
  Tables with nested or repeated fields cannot be exported in CSV format.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        '--async', help='Create an asynchronous job to perform the import.',
        action='store_true')
    parser.add_argument(
        '--destination-format',
        choices=['csv', 'newline-delimited-json'],
        help='The format in which the exported data is to be written')
    parser.add_argument(
        '--field-delimiter',
        default=',',
        help='The character that indicates the boundary between columns in '
        'CSV output. "\t" and "tab" are accepted names for tab.')
    parser.add_argument(
        '--job-id',
        help='A unique job_id to use for the request. If this flag is not '
        'specified, a job_id will be generated automatically and displayed as '
        'the result of the command.')
    parser.add_argument(
        '--status',
        choices=[
            job_progress.STATUS_REPORTING_PERIODIC,
            job_progress.STATUS_REPORTING_CHANGES,
            job_progress.STATUS_REPORTING_NONE],
        default=job_progress.STATUS_REPORTING_PERIODIC,
        help='Whether the status of the export job should be reported '
        'periodically, every time the status changes, or not at all.')
    parser.add_argument(
        'source_table', help='The table whose data is to be exported')
    parser.add_argument(
        'destination_uri',
        nargs='+',
        help='A Google Storage URI specifying a file where the exported data '
        'is to be stored.')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace, All the arguments that were provided to this
        command invocation.

    Raises:
      ToolException: when destination uri is not specified or invalid.
    """
    apitools_client = self.context[commands.APITOOLS_CLIENT_KEY]
    bigquery_messages = self.context[commands.BIGQUERY_MESSAGES_MODULE_KEY]
    resource_parser = self.context[commands.BIGQUERY_REGISTRY_KEY]
    project_id = properties.VALUES.core.project.Get(required=True)
    source_table_resource = resource_parser.Parse(
        args.source_table, collection='bigquery.tables')
    source_table_reference = message_conversions.TableResourceToReference(
        bigquery_messages, source_table_resource)

    if not args.destination_uri:
      raise exceptions.ToolException(
          'At least one destination URI must be specified.')
    destination_uris = args.destination_uri
    for uri in destination_uris:
      if not uri.startswith('gs://'):
        raise exceptions.ToolException(
            ('Illegal URI: {0}. Only Google Storage ("gs://") URIs are '
             'supported.').format(uri))

    job = job_control.ExecuteJob(
        apitools_client,
        bigquery_messages,
        args,
        configuration=bigquery_messages.JobConfiguration(
            extract=bigquery_messages.JobConfigurationExtract(
                sourceTable=source_table_reference,
                destinationUris=destination_uris,
                destinationFormat=bigquery_client_helper.NormalizeTextualFormat(
                    args.destination_format),
                fieldDelimiter=bigquery_client_helper.NormalizeFieldDelimiter(
                    args.field_delimiter))),
        async=args.async,
        project_id=project_id,
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
