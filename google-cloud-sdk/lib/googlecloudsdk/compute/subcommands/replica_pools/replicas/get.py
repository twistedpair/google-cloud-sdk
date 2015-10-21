# Copyright 2014 Google Inc. All Rights Reserved.

"""replicapool replicas get command."""

from apiclient import errors
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import properties

from googlecloudsdk.shared.compute import rolling_updates_util as util


class Get(base.Command):
  """Get information about a single replica in a replica pool.

  *{command}* gets information about a single replica in a replica pool.

  By default, this information is displayed in yaml format.
  You can also specify json or text formats.
  """

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
    """Run 'replicapool replicas get'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Raises:
      HttpException: A http error response was received while executing api
          request.
      ToolException: An error other than http error occured while executing
          the command.

    Returns:
      The get API's response
    """
    client = self.context['replicapool']
    project = properties.VALUES.core.project.Get(required=True)

    request = client.replicas().get(
        projectName=project, zone=args.zone, poolName=args.pool,
        replicaName=args.replica)

    try:
      response = request.execute()
      util.PrettyPrint(response, args.format or 'yaml')
      return response
    except errors.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))
    except errors.Error as error:
      raise exceptions.ToolException(error)
