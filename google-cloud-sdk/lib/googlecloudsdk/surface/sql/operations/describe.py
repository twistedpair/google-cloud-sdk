# Copyright 2013 Google Inc. All Rights Reserved.

"""Retrieves information about a Cloud SQL instance operation."""

from googlecloudsdk.api_lib.sql import errors
from googlecloudsdk.api_lib.sql import validate
from googlecloudsdk.calliope import base


class _BaseGet(object):
  """Base class for sql get operations."""

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
        help='Name that uniquely identifies the operation.')

  def Display(self, unused_args, result):
    """Display prints information about what just happened to stdout.

    Args:
      unused_args: The same as the args in Run.
      result: A dict object representing the operations resource if the api
      request was successful.
    """
    self.format(result)


@base.ReleaseTracks(base.ReleaseTrack.GA)
class Get(_BaseGet, base.Command):
  """Retrieves information about a Cloud SQL instance operation."""

  @errors.ReraiseHttpException
  def Run(self, args):
    """Retrieves information about a Cloud SQL instance operation.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A dict object representing the operations resource if the api request was
      successful.
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

    operation_ref = resources.Parse(
        args.operation, collection='sql.operations',
        params={'project': instance_ref.project,
                'instance': instance_ref.instance})

    result = sql_client.operations.Get(operation_ref.Request())
    return result


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class GetBeta(_BaseGet, base.Command):
  """Retrieves information about a Cloud SQL instance operation."""

  @errors.ReraiseHttpException
  def Run(self, args):
    """Retrieves information about a Cloud SQL instance operation.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A dict object representing the operations resource if the api request was
      successful.
    Raises:
      HttpException: A http error response was received while executing api
          request.
      ToolException: An error other than http error occured while executing the
          command.
    """
    sql_client = self.context['sql_client']
    resources = self.context['registry']

    operation_ref = resources.Parse(
        args.operation, collection='sql.operations',
        params={'project': args.project})

    result = sql_client.operations.Get(operation_ref.Request())
    return result
