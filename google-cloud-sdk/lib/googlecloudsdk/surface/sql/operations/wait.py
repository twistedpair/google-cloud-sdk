# Copyright 2014 Google Inc. All Rights Reserved.

"""Retrieves information about a Cloud SQL instance operation."""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import list_printer
from googlecloudsdk.shared.sql import errors
from googlecloudsdk.shared.sql import operations
from googlecloudsdk.shared.sql import validate


class _BaseWait(object):
  """Base class for sql wait operations."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use it to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument(
        'operation',
        nargs='+',
        help='An identifier that uniquely identifies the operation.')


@base.ReleaseTracks(base.ReleaseTrack.GA)
class Wait(_BaseWait, base.Command):
  """Waits for one or more operations to complete."""

  @errors.ReraiseHttpException
  def Run(self, args):
    """Wait for a Cloud SQL instance operation.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Yields:
      Operations that were waited for.
    Raises:
      HttpException: A http error response was received while executing api
          request.
      ToolException: An error other than http error occured while executing the
          command.
    """
    sql_client = self.context['sql_client']
    resources = self.context['registry']

    validate.ValidateInstanceName(args.instance)
    instance_ref = resources.Parse(args.instance, collection='sql.instances')

    for op in args.operation:
      operation_ref = resources.Parse(
          op, collection='sql.operations',
          params={'project': instance_ref.project,
                  'instance': instance_ref.instance})

      operations.OperationsV1Beta3.WaitForOperation(
          sql_client, operation_ref,
          'Waiting for [{operation}]'.format(operation=operation_ref))
      yield sql_client.operations.Get(operation_ref.Request())

  def Display(self, unused_args, result):
    list_printer.PrintResourceList('sql.operations', result)


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class WaitBeta(_BaseWait, base.Command):
  """Waits for one or more operations to complete."""

  @errors.ReraiseHttpException
  def Run(self, args):
    """Wait for a Cloud SQL instance operation.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Yields:
      Operations that were waited for.
    Raises:
      HttpException: A http error response was received while executing api
          request.
      ToolException: An error other than http error occured while executing the
          command.
    """
    sql_client = self.context['sql_client']
    resources = self.context['registry']

    for op in args.operation:
      operation_ref = resources.Parse(
          op, collection='sql.operations',
          params={'project': args.project})

      operations.OperationsV1Beta4.WaitForOperation(
          sql_client, operation_ref,
          'Waiting for [{operation}]'.format(operation=operation_ref))
      yield sql_client.operations.Get(operation_ref.Request())

  def Display(self, unused_args, result):
    list_printer.PrintResourceList('sql.operations.v1beta4', result)
