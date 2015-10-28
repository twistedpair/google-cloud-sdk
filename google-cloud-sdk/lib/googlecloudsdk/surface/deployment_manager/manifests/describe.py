# Copyright 2014 Google Inc. All Rights Reserved.

"""manifests describe command."""

from googlecloudsdk.api_lib.deployment_manager import dm_v2_util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resource_printer
from googlecloudsdk.third_party.apitools.base import py as apitools_base


class Describe(base.Command):
  """Provide information about a manifest.

  This command prints out all available details about a manifest.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To display information about a manifest, run:

            $ {command} --deployment my-deployment manifest-name
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
    parser.add_argument('manifest', help='Manifest name.')

  def Run(self, args):
    """Run 'manifests describe'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      The requested manifest.

    Raises:
      HttpException: An http error response was received while executing api
          request.
    """
    client = self.context['deploymentmanager-client']
    messages = self.context['deploymentmanager-messages']
    project = properties.VALUES.core.project.Get(required=True)

    try:
      return client.manifests.Get(
          messages.DeploymentmanagerManifestsGetRequest(
              project=project,
              deployment=args.deployment,
              manifest=args.manifest,
          )
      )
    except apitools_base.HttpError as error:
      raise exceptions.HttpException(dm_v2_util.GetError(error))

  def Display(self, unused_args, result):
    """Display prints information about what just happened to stdout.

    Args:
      unused_args: The same as the args in Run.

      result: a Manifest object to display.

    Raises:
      ValueError: if result is None or not a Manifest
    """
    messages = self.context['deploymentmanager-messages']
    if not isinstance(result, messages.Manifest):
      raise ValueError('result must be a Manifest')

    resource_printer.Print(resources=result,
                           print_format=unused_args.format or 'yaml',
                           out=log.out)
