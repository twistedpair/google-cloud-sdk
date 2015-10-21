# Copyright 2014 Google Inc. All Rights Reserved.

"""replicapool replicas delete command."""

from apiclient import errors
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties

from googlecloudsdk.shared.compute import rolling_updates_util as util


class Delete(base.Command):
  """Deletes a single replica from a replica pool."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument('replica', help='Replica name.')
    parser.add_argument(
        '--abandon-instance',
        action='store_true',
        help='If provided, abandon the instance: leave the instance '
        'behind and delete the Replica. Instance is deleted along with the '
        'Replica if this flag is not provided.')

  def Run(self, args):
    """Run 'replicapool replicas delete'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Raises:
      HttpException: An http error response was received while executing api
          request.
      ToolException: An error other than http error occurred while executing
          the command.
    """
    client = self.context['replicapool']
    project = properties.VALUES.core.project.Get(required=True)

    delete_body = {}
    if args.abandon_instance:
      delete_body['abandonInstance'] = args.abandon_instance is True

    request = client.replicas().delete(
        projectName=project, zone=args.zone, poolName=args.pool,
        replicaName=args.replica, body=delete_body)

    try:
      request.execute()
      log.Print('Replica {0} in pool {1} is being deleted.'.format(
          args.replica, args.pool))
    except errors.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))
    except errors.Error as error:
      raise exceptions.ToolException(error)

Delete.detailed_help = {
    'brief': 'Deletes a single replica from a replica pool.',
    'DESCRIPTION': """\
        This command deletes a single replica from a replica pool.

        By default, deleting a replica also deletes the underlying
        virtual machine instance. To keep the virtual machine instance,
        but delete the replica, provide the --abandon-instance flag.
        """,
}
