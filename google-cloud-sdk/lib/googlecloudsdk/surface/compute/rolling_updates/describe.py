# Copyright 2014 Google Inc. All Rights Reserved.

"""rolling-updates describe command."""
from googlecloudsdk.api_lib.compute import rolling_updates_util as updater_util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.third_party.apitools.base import py as apitools_base


class Describe(base.Command):
  """Gets information about a single update."""

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
    """Run 'rolling-updates describe'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      Update, representation of the update if the Get call was
      successful.

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
    request = messages.ReplicapoolupdaterRollingUpdatesGetRequest(
        project=ref.project,
        zone=ref.zone,
        rollingUpdate=ref.rollingUpdate)

    try:
      return client.rollingUpdates.Get(request)
    except apitools_base.HttpError as error:
      raise exceptions.HttpException(updater_util.GetError(error))

  def Display(self, args, result):
    self.format(result)


Describe.detailed_help = {
    'brief': 'Gets information about a single update.',
    'DESCRIPTION': """\
        This command gets information about a single update.

        By default, this information is displayed in yaml format.
        You can also specify json or text formats.
        """,
}
