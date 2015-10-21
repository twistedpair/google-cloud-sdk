# Copyright 2013 Google Inc. All Rights Reserved.

"""Promotes Cloud SQL read replica to a stand-alone instance."""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.shared.sql import errors
from googlecloudsdk.shared.sql import operations
from googlecloudsdk.shared.sql import validate


class _BasePromoteReplica(object):
  """Promotes Cloud SQL read replica to a stand-alone instance."""

  @classmethod
  def Args(cls, parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument('replica',
                        completion_resource='sql.instances',
                        help='Cloud SQL read replica ID.')
    parser.add_argument(
        '--async',
        action='store_true',
        help='Do not wait for the operation to complete.')

  def Display(self, unused_args, result):
    """Display information about what just happened to stdout.

    Args:
      unused_args: The same as the args in Run.
      result: A dict object representing the operations resource describing the
          promote-replica operation if the promote-replica was successful.
    """
    self.format(result)


@base.ReleaseTracks(base.ReleaseTrack.GA)
class PromoteReplica(_BasePromoteReplica, base.Command):
  """Promotes Cloud SQL read replica to a stand-alone instance."""

  @errors.ReraiseHttpException
  def Run(self, args):
    """Promotes Cloud SQL read replica to a stand-alone instance.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A dict object representing the operations resource describing the
      promote-replica operation if the promote-replica was successful.
    Raises:
      HttpException: An HTTP error response was received while executing api
          request.
      ToolException: An error other than an HTTP error occured while executing
          the command.
    """
    sql_client = self.context['sql_client']
    sql_messages = self.context['sql_messages']
    resources = self.context['registry']

    validate.ValidateInstanceName(args.replica)
    instance_ref = resources.Parse(args.replica, collection='sql.instances')

    result = sql_client.instances.PromoteReplica(
        sql_messages.SqlInstancesPromoteReplicaRequest(
            project=instance_ref.project,
            instance=instance_ref.instance))
    operation_ref = resources.Create(
        'sql.operations',
        operation=result.operation,
        project=instance_ref.project,
        instance=instance_ref.instance,
    )

    if args.async:
      return sql_client.operations.Get(operation_ref.Request())

    operations.OperationsV1Beta3.WaitForOperation(
        sql_client, operation_ref, 'Promoting Cloud SQL replica')

    log.status.write(
        'Promoted [{instance}].\n'.format(instance=instance_ref))


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class PromoteReplicaBeta(_BasePromoteReplica, base.Command):
  """Promotes Cloud SQL read replica to a stand-alone instance."""

  @errors.ReraiseHttpException
  def Run(self, args):
    """Promotes Cloud SQL read replica to a stand-alone instance.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A dict object representing the operations resource describing the
      promote-replica operation if the promote-replica was successful.
    Raises:
      HttpException: An HTTP error response was received while executing api
          request.
      ToolException: An error other than an HTTP error occured while executing
          the command.
    """
    sql_client = self.context['sql_client']
    sql_messages = self.context['sql_messages']
    resources = self.context['registry']

    validate.ValidateInstanceName(args.replica)
    instance_ref = resources.Parse(args.replica, collection='sql.instances')

    result = sql_client.instances.PromoteReplica(
        sql_messages.SqlInstancesPromoteReplicaRequest(
            project=instance_ref.project,
            instance=instance_ref.instance))
    operation_ref = resources.Create(
        'sql.operations',
        operation=result.name,
        project=instance_ref.project,
        instance=instance_ref.instance,
    )

    if args.async:
      return sql_client.operations.Get(operation_ref.Request())

    operations.OperationsV1Beta4.WaitForOperation(
        sql_client, operation_ref, 'Promoting Cloud SQL replica')

    log.status.write(
        'Promoted [{instance}].\n'.format(instance=instance_ref))
