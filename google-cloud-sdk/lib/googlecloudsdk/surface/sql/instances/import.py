# Copyright 2013 Google Inc. All Rights Reserved.

"""Imports data into a Cloud SQL instance.

Imports data into a Cloud SQL instance from a MySQL dump file in
Google Cloud Storage.
"""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.shared.sql import errors
from googlecloudsdk.shared.sql import operations
from googlecloudsdk.shared.sql import validate


class _BaseImport(object):
  """Imports data into a Cloud SQL instance from Google Cloud Storage."""

  def Display(self, unused_args, result):
    """Display prints information about what just happened to stdout.

    Args:
      unused_args: The same as the args in Run.
      result: A dict object representing the operations resource describing the
      import operation if the import was successful.
    """
    if result:
      self.format(result)


@base.ReleaseTracks(base.ReleaseTrack.GA)
class Import(_BaseImport, base.Command):
  """Imports data into a Cloud SQL instance from Google Cloud Storage."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument(
        'instance',
        completion_resource='sql.instances',
        help='Cloud SQL instance ID.')
    parser.add_argument(
        'uri',
        nargs='+',
        type=str,
        help='Path to the MySQL dump file in Google Cloud Storage from which'
        ' the import is made. The URI is in the form gs://bucketName/fileName.'
        ' Compressed gzip files (.gz) are also supported.')
    parser.add_argument(
        '--database',
        '-d',
        required=False,
        help='The database (for example, guestbook) to which the import is'
        ' made. If not set, it is assumed that the database is specified in'
        ' the file to be imported.')
    parser.add_argument(
        '--async',
        action='store_true',
        help='Do not wait for the operation to complete.')

  @errors.ReraiseHttpException
  def Run(self, args):
    """Imports data into a Cloud SQL instance from Google Cloud Storage.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A dict object representing the operations resource describing the import
      operation if the import was successful.
    Raises:
      HttpException: A http error response was received while executing api
          request.
      ToolException: An error other than http error occured while executing the
          command.
    """
    sql_client = self.context['sql_client']
    sql_messages = self.context['sql_messages']
    resources = self.context['registry']

    validate.ValidateInstanceName(args.instance)
    instance_ref = resources.Parse(args.instance, collection='sql.instances')

    import_request = sql_messages.SqlInstancesImportRequest(
        instance=instance_ref.instance,
        project=instance_ref.project,
        instancesImportRequest=sql_messages.InstancesImportRequest(
            importContext=sql_messages.ImportContext(
                uri=args.uri,
                database=args.database,
            ),
        ),
    )

    result = sql_client.instances.Import(import_request)

    operation_ref = resources.Create(
        'sql.operations',
        operation=result.operation,
        project=instance_ref.project,
        instance=instance_ref.instance,
    )

    if args.async:
      return sql_client.operations.Get(operation_ref.Request())

    operations.OperationsV1Beta3.WaitForOperation(
        sql_client, operation_ref, 'Importing Cloud SQL instance')

    log.status.write('Imported [{instance}] from [{buckets}].\n'.format(
        instance=instance_ref, buckets=','.join(args.uri)))

    return None


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class ImportBeta(_BaseImport, base.Command):
  """Imports data into a Cloud SQL instance from Google Cloud Storage."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument(
        'instance',
        completion_resource='sql.instances',
        help='Cloud SQL instance ID.')
    parser.add_argument(
        'uri',
        type=str,
        help='Path to the MySQL dump file in Google Cloud Storage from which'
        ' the import is made. The URI is in the form gs://bucketName/fileName.'
        ' Compressed gzip files (.gz) are also supported.')
    parser.add_argument(
        '--database',
        '-d',
        required=False,
        help='The database (for example, guestbook) to which the import is'
        ' made. If not set, it is assumed that the database is specified in'
        ' the file to be imported.')
    parser.add_argument(
        '--async',
        action='store_true',
        help='Do not wait for the operation to complete.')

  @errors.ReraiseHttpException
  def Run(self, args):
    """Imports data into a Cloud SQL instance from Google Cloud Storage.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A dict object representing the operations resource describing the import
      operation if the import was successful.
    Raises:
      HttpException: A http error response was received while executing api
          request.
      ToolException: An error other than http error occured while executing the
          command.
    """
    sql_client = self.context['sql_client']
    sql_messages = self.context['sql_messages']
    resources = self.context['registry']

    validate.ValidateInstanceName(args.instance)
    instance_ref = resources.Parse(args.instance, collection='sql.instances')

    # TODO(svalentin): support CSV import
    import_request = sql_messages.SqlInstancesImportRequest(
        instance=instance_ref.instance,
        project=instance_ref.project,
        instancesImportRequest=sql_messages.InstancesImportRequest(
            importContext=sql_messages.ImportContext(
                uri=args.uri,
                database=args.database,
                fileType='SQL',
            ),
        ),
    )

    result_operation = sql_client.instances.Import(import_request)

    operation_ref = resources.Create(
        'sql.operations',
        operation=result_operation.name,
        project=instance_ref.project,
        instance=instance_ref.instance,
    )

    if args.async:
      return sql_client.operations.Get(operation_ref.Request())

    operations.OperationsV1Beta4.WaitForOperation(
        sql_client, operation_ref, 'Importing Cloud SQL instance')

    log.status.write('Imported [{instance}] from [{bucket}].\n'.format(
        instance=instance_ref, bucket=args.uri))

    return None
