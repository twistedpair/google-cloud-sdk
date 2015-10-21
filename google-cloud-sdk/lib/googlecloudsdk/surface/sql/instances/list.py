# Copyright 2013 Google Inc. All Rights Reserved.

"""Lists instances in a given project.

Lists instances in a given project in the alphabetical order of the
 instance name.
"""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import properties
from googlecloudsdk.core import remote_completion
from googlecloudsdk.core import resources
from googlecloudsdk.shared.sql import errors
from googlecloudsdk.third_party.apitools.base import py as apitools_base


class _BaseList(object):
  """Lists Cloud SQL instances in a given project."""

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
        default=None,
        type=int,
        help='Maximum number of instances to list.')

  @errors.ReraiseHttpException
  def Run(self, args):
    """Lists Cloud SQL instances in a given project.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      SQL instance resource iterator.
    Raises:
      HttpException: An http error response was received while executing api
          request.
      ToolException: An error other than an http error occured while executing
          the command.
    """
    sql_client = self.context['sql_client']
    sql_messages = self.context['sql_messages']

    project_id = properties.VALUES.core.project.Get(required=True)

    remote_completion.SetGetInstanceFun(self.GetRef)
    return apitools_base.YieldFromList(
        sql_client.instances,
        sql_messages.SqlInstancesListRequest(project=project_id),
        args.limit)


@base.ReleaseTracks(base.ReleaseTrack.GA)
class List(_BaseList, base.Command):
  """Lists Cloud SQL instances in a given project.

  Lists Cloud SQL instances in a given project in the alphabetical
  order of the instance name.
  """

  @staticmethod
  def GetRef(item):
    instance_ref = resources.Create('sql.instances', project=item.project,
                                    instance=item.instance)
    return instance_ref.SelfLink()

  def Display(self, unused_args, result):
    instance_refs = []
    items = remote_completion.Iterate(result, instance_refs, self.GetRef)
    list_printer.PrintResourceList('sql.instances', items)
    cache = remote_completion.RemoteCompletion()
    cache.StoreInCache(instance_refs)


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class ListBeta(_BaseList, base.Command):
  """Lists Cloud SQL instances in a given project.

  Lists Cloud SQL instances in a given project in the alphabetical
  order of the instance name.
  """

  @staticmethod
  def GetRef(item):
    instance_ref = resources.Create('sql.instances', project=item.project,
                                    instance=item.name)
    return instance_ref.SelfLink()

  def Display(self, unused_args, result):
    instance_refs = []
    items = remote_completion.Iterate(result, instance_refs, self.GetRef)
    list_printer.PrintResourceList('sql.instances.v1beta4', items)
    cache = remote_completion.RemoteCompletion()
    cache.StoreInCache(instance_refs)
