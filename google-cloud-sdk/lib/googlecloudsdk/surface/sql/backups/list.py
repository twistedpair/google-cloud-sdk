# Copyright 2013 Google Inc. All Rights Reserved.

"""Lists all backups associated with a given instance.

Lists all backups associated with a given instance and configuration
in the reverse chronological order of the enqueued time.
"""

from googlecloudsdk.api_lib.sql import errors
from googlecloudsdk.api_lib.sql import validate
from googlecloudsdk.calliope import base
from googlecloudsdk.core import list_printer
from googlecloudsdk.third_party.apitools.base import py as apitools_base


class _BaseList(object):
  """Base class for sql backups list."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use it to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument(
        '--limit',
        type=int,
        required=False,
        default=None,
        help='Maximum number of backups to list.')


@base.ReleaseTracks(base.ReleaseTrack.GA)
class List(_BaseList, base.Command):
  """Lists all backups associated with a given instance.

  Lists all backups associated with a given Cloud SQL instance and
  configuration in the reverse chronological order of the enqueued time.
  """

  @errors.ReraiseHttpException
  def Run(self, args):
    """Lists all backups associated with a given instance.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A dict object that has the list of backup run resources if the command ran
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

    instance_resource = sql_client.instances.Get(instance_ref.Request())
    config_id = instance_resource.settings.backupConfiguration[0].id

    return apitools_base.YieldFromList(
        sql_client.backupRuns,
        sql_messages.SqlBackupRunsListRequest(
            project=instance_ref.project,
            instance=instance_ref.instance,
            # At this point we support only one backup-config. So, we just use
            # that id.
            backupConfiguration=config_id),
        args.limit)

  def Display(self, unused_args, result):
    list_printer.PrintResourceList('sql.backupRuns', result)


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class ListBeta(_BaseList, base.Command):
  """Lists all backups associated with a given instance.

  Lists all backups associated with a given Cloud SQL instance and
  configuration in the reverse chronological order of the enqueued time.
  """

  @errors.ReraiseHttpException
  def Run(self, args):
    """Lists all backups associated with a given instance.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A dict object that has the list of backup run resources if the command ran
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

    return apitools_base.YieldFromList(
        sql_client.backupRuns,
        sql_messages.SqlBackupRunsListRequest(
            project=instance_ref.project,
            instance=instance_ref.instance),
        args.limit)

  def Display(self, unused_args, result):
    list_printer.PrintResourceList('sql.backupRuns.v1beta4', result)
