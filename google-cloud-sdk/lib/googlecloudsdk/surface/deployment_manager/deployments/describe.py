# Copyright 2014 Google Inc. All Rights Reserved.

"""deployments describe command."""

from googlecloudsdk.api_lib.deployment_manager import dm_v2_util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resource_printer
from googlecloudsdk.third_party.apitools.base import py as apitools_base


class Describe(base.Command):
  """Provide information about a deployment.

  This command prints out all available details about a deployment.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To display information about a deployment, run:

            $ {command} my-deployment
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
    parser.add_argument('deployment_name', help='Deployment name.')

  def Run(self, args):
    """Run 'deployments describe'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      The requested Deployment.

    Raises:
      HttpException: An http error response was received while executing api
          request.
    """
    client = self.context['deploymentmanager-client']
    messages = self.context['deploymentmanager-messages']
    project = properties.VALUES.core.project.Get(required=True)

    try:
      return client.deployments.Get(
          messages.DeploymentmanagerDeploymentsGetRequest(
              project=project, deployment=args.deployment_name))
    except apitools_base.HttpError as error:
      raise exceptions.HttpException(dm_v2_util.GetError(error))

  def Display(self, unused_args, deployment):
    """Display prints information about what just happened to stdout.

    Args:
      unused_args: The same as the args in Run.

      deployment: a Deployment to print

    Raises:
      ValueError: if result is None or not a deployment
    """
    client = self.context['deploymentmanager-client']
    messages = self.context['deploymentmanager-messages']
    if not isinstance(deployment, messages.Deployment):
      raise ValueError('result must be a Deployment')

    # Get resources belonging to the deployment to display
    project = properties.VALUES.core.project.Get(required=True)
    resources = None
    try:
      response = client.resources.List(
          messages.DeploymentmanagerResourcesListRequest(
              project=project, deployment=deployment.name))
      resources = response.resources
    except apitools_base.HttpError:
      pass  # Couldn't get resources, skip adding them to the table.
    resource_printer.Print(resources=deployment,
                           print_format=unused_args.format or 'yaml',
                           out=log.out)
    if resources:
      log.Print('resources:')
      list_printer.PrintResourceList('deploymentmanagerv2.resources',
                                     resources)
