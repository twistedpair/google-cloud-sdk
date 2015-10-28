# Copyright 2013 Google Inc. All Rights Reserved.

"""Restores a backup of a Cloud SQL instance."""

from googlecloudsdk.api_lib.sql import errors
from googlecloudsdk.api_lib.sql import operations
from googlecloudsdk.api_lib.sql import validate
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log


class _BaseRestoreBackup(object):
  """Restores a backup of a Cloud SQL instance."""

  def Display(self, unused_args, result):
    """Display prints information about what just happened to stdout.

    Args:
      unused_args: The same as the args in Run.
      result: A dict object representing the operations resource describing the
      restoreBackup operation if the restoreBackup was successful.
    """
    self.format(result)


@base.ReleaseTracks(base.ReleaseTrack.GA)
class RestoreBackup(_BaseRestoreBackup, base.Command):
  """Restores a backup of a Cloud SQL instance."""

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
        '--due-time',
        '-d',
        required=True,
        help='The time when this run was due to start in RFC 3339 format, for '
        'example 2012-11-15T16:19:00.094Z.')
    parser.add_argument(
        '--async',
        action='store_true',
        help='Do not wait for the operation to complete.')

  @errors.ReraiseHttpException
  def Run(self, args):
    """Restores a backup of a Cloud SQL instance.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A dict object representing the operations resource describing the
      restoreBackup operation if the restoreBackup was successful.
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

    instance_resource = sql_client.instances.Get(instance_ref.Request())
    # At this point we support only one backup-config. So, just use that id.
    backup_config = instance_resource.settings.backupConfiguration[0].id

    result = sql_client.instances.RestoreBackup(
        sql_messages.SqlInstancesRestoreBackupRequest(
            project=instance_ref.project,
            instance=instance_ref.instance,
            backupConfiguration=backup_config,
            dueTime=args.due_time))

    operation_ref = resources.Create(
        'sql.operations',
        operation=result.operation,
        project=instance_ref.project,
        instance=instance_ref.instance,
    )

    if args.async:
      return sql_client.operations.Get(operation_ref.Request())

    operations.OperationsV1Beta3.WaitForOperation(
        sql_client, operation_ref, 'Restoring Cloud SQL instance')

    log.status.write('Restored [{instance}].\n'.format(
        instance=instance_ref))

    return None


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class RestoreBackupBeta(_BaseRestoreBackup, base.Command):
  """Restores a backup of a Cloud SQL instance."""

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
        help='Cloud SQL instance ID that will be restored.')
    parser.add_argument(
        '--backup-id',
        '-b',
        type=int,
        required=True,
        help='The ID of the backup run to restore from.')
    parser.add_argument(
        '--backup-instance',
        completion_resource='sql.instances',
        help='The ID of the instance that the backup was taken from.')
    parser.add_argument(
        '--async',
        action='store_true',
        help='Do not wait for the operation to complete.')

  @errors.ReraiseHttpException
  def Run(self, args):
    """Restores a backup of a Cloud SQL instance.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A dict object representing the operations resource describing the
      restoreBackup operation if the restoreBackup was successful.
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

    if not args.backup_instance:
      args.backup_instance = args.instance

    result_operation = sql_client.instances.RestoreBackup(
        sql_messages.SqlInstancesRestoreBackupRequest(
            project=instance_ref.project,
            instance=instance_ref.instance,
            instancesRestoreBackupRequest=(
                sql_messages.InstancesRestoreBackupRequest(
                    restoreBackupContext=sql_messages.RestoreBackupContext(
                        backupRunId=args.backup_id,
                        instanceId=args.backup_instance,
                    )
                )
            )
        )
    )

    operation_ref = resources.Create(
        'sql.operations',
        operation=result_operation.name,
        project=instance_ref.project,
        instance=instance_ref.instance,
    )

    if args.async:
      return sql_client.operations.Get(operation_ref.Request())

    operations.OperationsV1Beta4.WaitForOperation(
        sql_client, operation_ref, 'Restoring Cloud SQL instance')

    log.status.write('Restored [{instance}].\n'.format(
        instance=instance_ref))

    return None
