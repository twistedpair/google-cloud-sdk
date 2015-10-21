# Copyright 2014 Google Inc. All Rights Reserved.

"""Implementation of gcloud bigquery copy.
"""

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io
from googlecloudsdk.shared.bigquery import bigquery
from googlecloudsdk.shared.bigquery import bigquery_client_helper
from googlecloudsdk.shared.bigquery import job_control
from googlecloudsdk.shared.bigquery import job_ids
from googlecloudsdk.shared.bigquery import job_progress
from googlecloudsdk.shared.bigquery import message_conversions
from googlecloudsdk.surface import bigquery as commands


class Copy(base.Command):
  """Copy one table to another.

  If the table does not exist, it is created. Otherwise, use --if-exist flag
  to choose desired behaviour.
  """

  detailed_help = {
      'EXAMPLES': """\
          To copy table from projectX to current project in datasetY:

            $ {command} projectX/datasetX/tableX datasetY/tableY
       """,
  }

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        '--async',
        action='store_true',
        help='If True, create an asynchronous job, and use the success of job '
        'creation as the error code. If False, wait for command completion '
        'before returning, and use the job completion status for error codes.')
    parser.add_argument(
        '--if-exists',
        choices=['append', 'fail', 'prompt', 'replace', 'skip'],
        default='prompt',
        help='What to do if the destination table already exists.')
    parser.add_argument(
        '--job-id',
        help='A unique job ID to use for the request.')
    parser.add_argument(
        '--status',
        choices=[
            job_progress.STATUS_REPORTING_PERIODIC,
            job_progress.STATUS_REPORTING_CHANGES,
            job_progress.STATUS_REPORTING_NONE],
        default=job_progress.STATUS_REPORTING_PERIODIC,
        help='Whether the status of the copying job should be reported '
        'periodically, every time the status changes, or not at all.')
    # TODO(jasmuth): Integrate progress tracking with console_io.ProgressTracker
    parser.add_argument('source', help='the table to be copied from')
    parser.add_argument('destination', help='the table to be copied to')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace, All the arguments that were provided to this
        command invocation.
    Returns:
      None
    Raises:
      bigqueryError.BigqueryError: If the source and destination files are not
        both specified.
      calliope_exceptions.ToolException: If user cancels this operation.
      Exception: If an unexpected value for the --if-exists flag passed gcloud
        validation (which should never happen)
    """
    apitools_client = self.context[commands.APITOOLS_CLIENT_KEY]
    bigquery_messages = self.context[commands.BIGQUERY_MESSAGES_MODULE_KEY]
    resource_parser = self.context[commands.BIGQUERY_REGISTRY_KEY]
    project_id = properties.VALUES.core.project.Get(required=True)

    source_reference = resource_parser.Parse(
        args.source, collection='bigquery.tables')
    source_reference_message = message_conversions.TableResourceToReference(
        bigquery_messages, source_reference)

    destination_resource = resource_parser.Parse(
        args.destination, collection='bigquery.tables')
    destination_reference = message_conversions.TableResourceToReference(
        bigquery_messages, destination_resource)

    if args.if_exists == 'append':
      write_disposition = 'WRITE_APPEND'
      ignore_already_exists = True
    elif args.if_exists == 'fail':
      write_disposition = 'WRITE_EMPTY'
      ignore_already_exists = False
    elif args.if_exists == 'prompt':
      write_disposition = 'WRITE_TRUNCATE'
      ignore_already_exists = False
      if bigquery_client_helper.TableExists(
          apitools_client, bigquery_messages, destination_reference):
        if not console_io.PromptContinue(
            prompt_string='Replace {0}'.format(destination_resource)):
          raise calliope_exceptions.ToolException('canceled by user')
    elif args.if_exists == 'replace':
      write_disposition = 'WRITE_TRUNCATE'
      ignore_already_exists = False
    elif args.if_exists == 'skip':
      if bigquery_client_helper.TableExists(
          apitools_client, bigquery_messages, destination_reference):
        return
    else:
      # This should be unreachable.
      raise core_exceptions.InternalError(
          'Unexpected value "{0}" for --if-exists flag.'.format(args.if_exists))

    copy_config = bigquery_messages.JobConfigurationTableCopy(
        sourceTable=source_reference_message,
        destinationTable=destination_reference,
        writeDisposition=write_disposition)

    job_id = job_ids.JobIdProvider().GetJobId(
        args.job_id, args.fingerprint_job_id)

    try:
      job = job_control.ExecuteJob(
          apitools_client,
          bigquery_messages,
          args,
          configuration=bigquery_messages.JobConfiguration(copy=copy_config),
          project_id=project_id,
          job_id=job_id)
    except bigquery.DuplicateError as e:
      if ignore_already_exists:
        job = None
      else:
        raise e

    if job is None:
      log.status.Print(
          'Table "{0}" already exists, skipping'.format(destination_resource))
    elif args.async:
      registry = self.context[commands.BIGQUERY_REGISTRY_KEY]
      job_resource = registry.Create(
          'bigquery.jobs',
          projectId=job.jobReference.projectId,
          jobId=job.jobReference.jobId)
      log.CreatedResource(job_resource)
    else:
      log.status.Print('Table [{0}] successfully copied to [{1}]'.format(
          source_reference, destination_resource))

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    pass
