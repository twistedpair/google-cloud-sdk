# Copyright 2014 Google Inc. All Rights Reserved.

"""operations list command."""

import types

from googlecloudsdk.calliope import base
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.third_party.apitools.base.py import list_pager


class List(base.Command):
  """List operations in a project.

  Prints a table with summary information on all operations in the project.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To print out a list of operations with some summary information about each, run:

            $ {command}

          To print only the name of each operation, run:

            $ {command} --simple-list
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
    """Run 'operations list'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      The list of operations for this project.

    Raises:
      HttpException: An http error response was received while executing api
          request.
    """
    client = self.context['deploymentmanager-client']
    messages = self.context['deploymentmanager-messages']
    project = properties.VALUES.core.project.Get(required=True)

    request = messages.DeploymentmanagerOperationsListRequest(
        project=project,
    )
    return list_pager.YieldFromList(
        client.operations, request, field='operations', limit=args.limit,
        batch_size=500)

  def Display(self, args, result):
    """Display prints information about what just happened to stdout.

    Args:
      args: The same as the args in Run.

      result: a generator of Operation objects.

    Raises:
      ValueError: if result is None or not a generator
    """
    if not isinstance(result, types.GeneratorType):
      raise ValueError('result must be a generator')

    if args.simple_list:
      empty_generator = True
      for operation in result:
        empty_generator = False
        log.Print(operation.name)
      if empty_generator:
        log.Print('No Operations were found in your project!')
    else:
      list_printer.PrintResourceList('deploymentmanagerv2.operations', result)
