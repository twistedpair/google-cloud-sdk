# Copyright 2014 Google Inc. All Rights Reserved.

"""replicapool create command."""

from apiclient import errors
from googlecloudsdk.api_lib.compute import replica_template_util
from googlecloudsdk.api_lib.compute import rolling_updates_util as util
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties


class Create(base.Command):
  """Insert (Create) a replica pool."""

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
        '--template',
        required=True,
        help='Path to YAML or JSON file containing the Replica pool template.')
    parser.add_argument(
        '--size',
        required=True,
        help='Initial number of replicas in replica pool')
    parser.add_argument('--description', help='Replica pool description.')
    parser.add_argument(
        '--target-pools',
        type=arg_parsers.ArgList(),
        metavar='TARGET_POOL',
        action=arg_parsers.FloatingListValuesCatcher(),
        help='Compute Engine Target Pools to add replicas to. Target Pools '
        'must be specified by name, not by URL. Example: '
        '--target-pools "target-pool-1,target-pool-2"')
    parser.add_argument(
        '--resource-views',
        type=arg_parsers.ArgList(),
        metavar='RESOURCE_VIEW',
        action=arg_parsers.FloatingListValuesCatcher(),
        help='Compute Engine Resource Views to add replicas to. Resource Views'
        ' must be specified by URL. Example: '
        '--resource-views "https://view-url1,https://view-url2"')
    parser.add_argument(
        '--auto-restart', action='store_true', default=True,
        help='Automatically restart unhealthy replicas in this Replica pool.')
    replica_template_util.AddTemplateParamArgs(parser)

  def Run(self, args):
    """Run 'replicapool create'.

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

    template = replica_template_util.ParseTemplate(
        args.template, params=args.param, params_from_file=args.param_from_file)

    new_replicapool = {
        'name': args.pool,
        'description': args.description,
        'numReplicas': args.size,
        'autoRestart': True,
        'template': template['template']
    }
    if not args.auto_restart:
      new_replicapool['autoRestart'] = False
    if args.target_pools:
      new_replicapool['targetPools'] = args.target_pools
    if args.resource_views:
      new_replicapool['resourceViews'] = args.resource_views

    request = client.pools().insert(
        projectName=project, zone=args.zone, body=new_replicapool)

    try:
      request.execute()
      log.Print('Replica pool {0} is being created.'.format(args.pool))
    except errors.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))
    except errors.Error as error:
      raise exceptions.ToolException(error)
