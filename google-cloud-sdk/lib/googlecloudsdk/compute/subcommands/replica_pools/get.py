# Copyright 2014 Google Inc. All Rights Reserved.

"""replicapool get command."""

from apiclient import errors
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import properties

from googlecloudsdk.shared.compute import rolling_updates_util as util


class Get(base.Command):
  """Gets information about a single replica pool."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument('pool', help='Replica pool name.')

  def Run(self, args):
    """Run 'replicapool get'.

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

    request = client.pools().get(
        projectName=project, zone=args.zone, poolName=args.pool)

    try:
      response = request.execute()
      util.PrettyPrint(response, args.format or 'yaml')
      return response
    except errors.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))
    except errors.Error as error:
      raise exceptions.ToolException(error)

Get.detailed_help = {
    'brief': 'Gets information about a single replica pool.',
    'DESCRIPTION': """\
        This command gets information about a single replica pool.

        By default, this information is displayed in yaml format.
        You can also specify json or text formats.
        """,
}
