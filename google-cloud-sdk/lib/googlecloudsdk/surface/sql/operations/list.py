# Copyright 2013 Google Inc. All Rights Reserved.

"""List all instance operations.

Lists all instance operations that have been performed on the given
Cloud SQL instance.
"""

from googlecloudsdk.api_lib.sql import errors
from googlecloudsdk.api_lib.sql import validate
from googlecloudsdk.calliope import base
from googlecloudsdk.core import list_printer
from googlecloudsdk.third_party.apitools.base.py import list_pager


class _BaseList(object):
  """Base class for sql list operations."""

  @errors.ReraiseHttpException
  def Run(self, args):
    """Lists all instance operations that have been performed on an instance.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A dict object that has the list of operation resources if the command ran
      successfully.
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

    return list_pager.YieldFromList(
        sql_client.operations,
        sql_messages.SqlOperationsListRequest(
            project=instance_ref.project,
            instance=instance_ref.instance),
        args.limit)


@base.ReleaseTracks(base.ReleaseTrack.GA)
class List(_BaseList, base.Command):
  """Lists all instance operations for the given Cloud SQL instance."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Maximum number of operations to list.')

  def Display(self, unused_args, result):
    list_printer.PrintResourceList('sql.operations', result)


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class ListBeta(_BaseList, base.Command):
  """Lists all instance operations for the given Cloud SQL instance."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Maximum number of operations to list.')
    parser.add_argument(
        '--instance',
        '-i',
        completion_resource='sql.instances',
        help='Cloud SQL instance ID.',
        required=True)

  def Display(self, unused_args, result):
    list_printer.PrintResourceList('sql.operations.v1beta4', result)
