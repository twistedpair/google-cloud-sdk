# Copyright 2014 Google Inc. All Rights Reserved.

"""rolling-updates cancel command."""

from googlecloudsdk.api_lib.compute import rolling_updates_util as updater_util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.third_party.apitools.base import py as apitools_base


class Cancel(base.Command):
  """Cancels an existing update."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument('update', help='Update id.')
    # TODO(witek): Support --async which does not wait for state transition.

  def Run(self, args):
    """Run 'rolling-updates cancel'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

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
    request = messages.ReplicapoolupdaterRollingUpdatesCancelRequest(
        project=ref.project,
        zone=ref.zone,
        rollingUpdate=ref.rollingUpdate)

    try:
      operation = client.rollingUpdates.Cancel(request)
      operation_ref = resources.Parse(
          operation.name,
          collection='replicapoolupdater.zoneOperations')
      result = updater_util.WaitForOperation(
          client, operation_ref, 'Cancelling the update')
      if result:
        log.status.write('Cancelled [{0}].\n'.format(ref))
      else:
        raise exceptions.ToolException('could not cancel [{0}]'.format(ref))

    except apitools_base.HttpError as error:
      raise exceptions.HttpException(updater_util.GetError(error))

Cancel.detailed_help = {
    'brief': 'Cancels an existing update.',
    'DESCRIPTION': """\
        Cancels the update in state PAUSED or CANCELLED (fails if the update \
        is in any other state).
        No-op if invoked in state CANCELLED.
        """,
}
