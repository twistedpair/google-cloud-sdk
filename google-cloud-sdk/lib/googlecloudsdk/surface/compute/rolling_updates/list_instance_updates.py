# Copyright 2014 Google Inc. All Rights Reserved.

"""rolling-updates list-instance-updates command."""
from googlecloudsdk.api_lib.compute import rolling_updates_util as updater_util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import list_printer
from googlecloudsdk.third_party.apitools.base import py as apitools_base


class ListInstanceUpdates(base.Command):
  """Lists all instance updates for a given update."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument('update', help='Update id.')

  def Run(self, args):
    """Run 'rolling-updates list-instance-updates'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      List of all the instance updates.

    Raises:
      HttpException: An http error response was received while executing api
          request.
      ToolException: An error other than http error occured while executing
          the command.
    """
    client = self.context['updater_api']
    messages = self.context['updater_messages']
    resources = self.context['updater_resources']

    ref = resources.Parse(
        args.update,
        collection='replicapoolupdater.rollingUpdates')
    request = (
        messages.ReplicapoolupdaterRollingUpdatesListInstanceUpdatesRequest(
            project=ref.project,
            zone=ref.zone,
            rollingUpdate=ref.rollingUpdate))

    try:
      return apitools_base.YieldFromList(
          client.rollingUpdates, request, method='ListInstanceUpdates')
    except apitools_base.HttpError as error:
      raise exceptions.HttpException(updater_util.GetError(error))

  def Display(self, unused_args, result):
    list_printer.PrintResourceList(
        'replicapoolupdater.rollingUpdates.instanceUpdates', result)
