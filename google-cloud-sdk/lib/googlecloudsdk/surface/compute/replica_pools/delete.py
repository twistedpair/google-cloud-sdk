# Copyright 2014 Google Inc. All Rights Reserved.

"""replicapool delete command."""

from apiclient import errors
from googlecloudsdk.api_lib.compute import rolling_updates_util as util
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties


class Delete(base.Command):
  """Deletes a replica pool and the corresponding replicas."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument('pool', help='Replica pool name.')
    parser.add_argument(
        '--abandon-instance',
        type=arg_parsers.ArgList(),
        metavar='INSTANCE',
        action=arg_parsers.FloatingListValuesCatcher(),
        required=False,
        default=None,
        help='Names of the instances to abandon, but not delete.')

  def Run(self, args):
    """Run 'replicapool delete'.

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

    delete_body = {}
    if args.abandon_instance:
      delete_body['abandonInstances'] = args.abandon_instance

    request = client.pools().delete(projectName=project, zone=args.zone,
                                    poolName=args.pool, body=delete_body)

    try:
      request.execute()
      log.Print('Replica pool {0} is being deleted.'.format(args.pool))
    except errors.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))
    except errors.Error as error:
      raise exceptions.ToolException(error)

Delete.detailed_help = {
    'brief': 'Deletes a replica pool and the corresponding replicas.',
    'DESCRIPTION': """\
        This command deletes a replica pool and the corresponding replicas.

        By default, the underlying virtual machine instances are also deleted.
        If you wish to keep the virtual machines, use the --abandon-instance flag.
        """,
}
