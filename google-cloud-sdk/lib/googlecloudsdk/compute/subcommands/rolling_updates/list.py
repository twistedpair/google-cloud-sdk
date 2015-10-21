# Copyright 2014 Google Inc. All Rights Reserved.

"""rolling-updates list command."""

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import properties
from googlecloudsdk.shared.compute import rolling_updates_util as updater_util
from googlecloudsdk.third_party.apitools.base import py as apitools_base


class List(base.Command):
  """Lists all updates for a given group."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument('--group',
                        help='Managed instance group name.')
    parser.add_argument('--limit', type=int,
                        help='The maximum number of results to list.')

  def Run(self, args):
    """Run 'rolling-updates list'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      List of all the updates.

    Raises:
      HttpException: An http error response was received while executing api
          request.
      ToolException: An error other than http error occured while executing
          the command.
    """
    client = self.context['updater_api']
    messages = self.context['updater_messages']

    request = messages.ReplicapoolupdaterRollingUpdatesListRequest(
        project=properties.VALUES.core.project.Get(required=True),
        zone=properties.VALUES.compute.zone.Get(required=True))
    if args.group:
      request.filter = 'instanceGroup eq %s' % args.group
    limit = updater_util.SanitizeLimitFlag(args.limit)

    try:
      return apitools_base.YieldFromList(client.rollingUpdates, request, limit)
    except apitools_base.HttpError as error:
      raise exceptions.HttpException(updater_util.GetError(error))

  def Display(self, unused_args, result):
    # TODO(user): Consider getting rid of instance group manager in api.
    def CoalescedInstanceGroupGenerator():
      for item in result:
        if item.instanceGroup:
          item.instanceGroupManager = item.instanceGroup
        yield item

    list_printer.PrintResourceList(
        'replicapoolupdater.rollingUpdates', CoalescedInstanceGroupGenerator())
