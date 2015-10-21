# Copyright 2014 Google Inc. All Rights Reserved.

"""resources list command."""

import types

from googlecloudsdk.calliope import base
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.third_party.apitools.base.py import list_pager


class List(base.Command):
  """List resources in a deployment.

  Prints a table with summary information on all resources in the deployment.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To print out a list of resources in the deployment with some summary information about each, run:

            $ {command} --deployment my-deployment

          To print only the name of each resource, run:

            $ {command} --deployment my-deployment --simple-list
          """,
  }

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument('--limit', type=int,
                        help='The maximum number of results to list.')
    parser.add_argument(
        '--simple-list',
        action='store_true',
        default=False,
        help='If true, only the list of resource IDs is printed. If false, '
        'prints a human-readable table of resource information.')

  def Run(self, args):
    """Run 'resources list'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      The list of resources for the specified deployment.

    Raises:
      HttpException: An http error response was received while executing api
          request.
    """
    client = self.context['deploymentmanager-client']
    messages = self.context['deploymentmanager-messages']
    project = properties.VALUES.core.project.Get(required=True)

    request = messages.DeploymentmanagerResourcesListRequest(
        project=project,
        deployment=args.deployment,
    )
    return list_pager.YieldFromList(
        client.resources, request, field='resources', limit=args.limit,
        batch_size=500)

  def Display(self, args, result):
    """Display prints information about what just happened to stdout.

    Args:
      args: The same as the args in Run.

      result: a generator of Resource objects.

    Raises:
      ValueError: if result is None or not a generator
    """
    if not isinstance(result, types.GeneratorType):
      raise ValueError('result must be a generator')

    if args.simple_list:
      empty_generator = True
      for resource in result:
        empty_generator = False
        log.Print(resource.name)
      if empty_generator:
        log.Print('No Resources were found in your deployment!')
    else:
      list_printer.PrintResourceList('deploymentmanagerv2.resources', result)
