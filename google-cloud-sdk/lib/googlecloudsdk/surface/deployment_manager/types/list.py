# Copyright 2014 Google Inc. All Rights Reserved.

"""operations list command."""

import types

from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.third_party.apitools.base.py import list_pager


class List(base.Command):
  """List types in a project.

  Prints a a list of the available resource types.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To print out a list of all available type names, run:

            $ {command}
          """,
  }

  def Run(self, args):
    """Run 'types list'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      The list of types for this project.

    Raises:
      HttpException: An http error response was received while executing api
          request.
    """
    client = self.context['deploymentmanager-client']
    messages = self.context['deploymentmanager-messages']
    project = properties.VALUES.core.project.Get(required=True)

    request = messages.DeploymentmanagerTypesListRequest(project=project)
    return list_pager.YieldFromList(client.types, request, field='types',
                                    batch_size=500)

  def Display(self, args, result):
    """Display prints information about what just happened to stdout.

    Args:
      args: The same as the args in Run.

      result: a list of types, where each dict is a Type object with a name
          attribute.

    Raises:
      ValueError: if result is None or not a generator
    """
    if not isinstance(result, types.GeneratorType):
      raise ValueError('result must be a generator')

    empty_generator = True
    for type_item in result:
      empty_generator = False
      log.Print(type_item.name)
    if empty_generator:
      log.Print('No types were found for your project!')
