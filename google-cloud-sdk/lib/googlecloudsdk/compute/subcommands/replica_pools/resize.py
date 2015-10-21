# Copyright 2014 Google Inc. All Rights Reserved.

"""replicapool resize command."""

from apiclient import errors
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties

from googlecloudsdk.shared.compute import rolling_updates_util as util


class Resize(base.Command):
  """Resizes a replica pool to a provided size."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument('pool', help='Replica pool name.')
    parser.add_argument('--new-size', required=True,
                        help='New size for the replica pool, must be >= 0.')

  def Run(self, args):
    """Run 'replicapool resize'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      An object representing the service response obtained by the Resize
      API if the Resize call was successful.

    Raises:
      HttpException: A http error response was received while executing api
          request.
      ToolException: An error other than http error occured while executing
          the command.
    """
    client = self.context['replicapool']
    project = properties.VALUES.core.project.Get(required=True)

    request = client.pools().resize(
        projectName=project, zone=args.zone, poolName=args.pool,
        numReplicas=args.new_size)

    try:
      request.execute()
      log.Print('Replica pool {0} is being resized.'.format(args.pool))
    except errors.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))
    except errors.Error as error:
      raise exceptions.ToolException(error)

Resize.detailed_help = {
    'brief': 'Resizes a replica pool to a provided size.',
    'DESCRIPTION': """\
        This command resizes a replica pool to a provided size.

        If you resize down, the Replica Pool service deletes replicas from the
        pool until the pool reaches the desired size. If you resize up, the Replica
        Pool service adds replicas to the pool using the most current template until
        the pool reaches the desired size.
        """,
}
