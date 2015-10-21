# Copyright 2014 Google Inc. All Rights Reserved.

"""manifests list command."""

import types

from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.third_party.apitools.base.py import list_pager


class List(base.Command):
  """List manifests in a deployment.

  Prints a table with summary information on all manifests in the deployment.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To print out a list of manifests in a deployment, run:

            $ {command} --deployment my-deployment

          To print only the name of each manifest, run:

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

  def Run(self, args):
    """Run 'manifests list'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      The list of manifests for the specified deployment.

    Raises:
      HttpException: An http error response was received while executing api
          request.
    """
    client = self.context['deploymentmanager-client']
    messages = self.context['deploymentmanager-messages']
    project = properties.VALUES.core.project.Get(required=True)

    request = messages.DeploymentmanagerManifestsListRequest(
        project=project,
        deployment=args.deployment,
    )
    return list_pager.YieldFromList(
        client.manifests, request, field='manifests', limit=args.limit,
        batch_size=500)

  def Display(self, unused_args, result):
    """Display prints information about what just happened to stdout.

    Args:
      unused_args: The same as the args in Run.

      result: a generator of Manifests, where each dict has a name attribute.

    Raises:
      ValueError: if result is None or not a generator
    """
    if not isinstance(result, types.GeneratorType):
      raise ValueError('result must be a generator')

    empty_generator = True
    for manifest in result:
      empty_generator = False
      log.Print(manifest.name)
    if empty_generator:
      log.Print('No Manifests were found in your deployment!')
