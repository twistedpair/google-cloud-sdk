# Copyright 2014 Google Inc. All Rights Reserved.

"""rolling-updates resume command."""

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.shared.compute import rolling_updates_util as updater_util
from googlecloudsdk.third_party.apitools.base import py as apitools_base


class Resume(base.Command):
  """Resume an existing update.

  Resumes the update in state ROLLING_FORWARD or PAUSED
  (fails if the update is in any other state).
  No-op if invoked in state ROLLED_OUT.

  Resume continues applying the new template and should be used
  when rollback was started, but the user decided to proceed with
  the update.
  """

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument('update', help='Update id.')
    # TODO(user): Support --async which does not wait for state transition.

  def Run(self, args):
    """Run 'rolling-updates resume'.

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
    request = messages.ReplicapoolupdaterRollingUpdatesResumeRequest(
        project=ref.project,
        zone=ref.zone,
        rollingUpdate=ref.rollingUpdate)

    try:
      operation = client.rollingUpdates.Resume(request)
      operation_ref = resources.Parse(
          operation.name,
          collection='replicapoolupdater.zoneOperations')
      result = updater_util.WaitForOperation(
          client, operation_ref, 'Resuming the update')
      if result:
        log.status.write('Resumed [{0}].\n'.format(ref))
      else:
        raise exceptions.ToolException('could not resume [{0}]'.format(ref))

    except apitools_base.HttpError as error:
      raise exceptions.HttpException(updater_util.GetError(error))
