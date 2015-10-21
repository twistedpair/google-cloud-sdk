# Copyright 2014 Google Inc. All Rights Reserved.

"""replicapool replicas restart command."""

from apiclient import errors
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties

from googlecloudsdk.shared.compute import rolling_updates_util as util


class Restart(base.Command):
  """Restart a single replica in a replica pool."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument('replica', help='Replica name.')

  def Run(self, args):
    """Run 'replicapool replicas restart'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Raises:
      HttpException: A http error response was received while executing api
          request.
      ToolException: An error other than http error occured while executing
          the command.
    """
    client = self.context['replicapool']
    project = properties.VALUES.core.project.Get(required=True)

    request = client.replicas().restart(
        projectName=project, zone=args.zone, poolName=args.pool,
        replicaName=args.replica)

    try:
      request.execute()
      log.Print('Replica {0} in pool {1} is being restarted.'.format(
          args.replica, args.pool))
    except errors.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))
    except errors.Error as error:
      raise exceptions.ToolException(error)

Restart.detailed_help = {
    'brief': 'Restart a single replica in a replica pool.',
    'DESCRIPTION': """\
        This command restarts a single replica in a replica pool.

        The restarted replica uses the most up-to-date replica pool template
        settings. This command can only restart one replica at a time.
        """,
}
