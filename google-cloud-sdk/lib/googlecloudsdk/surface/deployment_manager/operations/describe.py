# Copyright 2014 Google Inc. All Rights Reserved.

"""operations describe command."""

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resource_printer
from googlecloudsdk.shared.deployment_manager import dm_v2_util
from googlecloudsdk.third_party.apitools.base import py as apitools_base


class Describe(base.Command):
  """Provide information about an operation.

  This command prints out all available details about an operation.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To display information about an operation, run:

            $ {command} operation-name
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
    parser.add_argument('operation_name', help='Operation name.')

  def Run(self, args):
    """Run 'operations describe'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      The requested operation.

    Raises:
      HttpException: An http error response was received while executing api
          request.
    """
    client = self.context['deploymentmanager-client']
    messages = self.context['deploymentmanager-messages']
    project = properties.VALUES.core.project.Get(required=True)

    try:
      return client.operations.Get(
          messages.DeploymentmanagerOperationsGetRequest(
              project=project,
              operation=args.operation_name,
          )
      )
    except apitools_base.HttpError as error:
      raise exceptions.HttpException(dm_v2_util.GetError(error))

  def Display(self, unused_args, result):
    """Display prints information about what just happened to stdout.

    Args:
      unused_args: The same as the args in Run.

      result: an Operation to display

    Raises:
      ValueError: if result is None or not an Operation
    """
    messages = self.context['deploymentmanager-messages']
    if not isinstance(result, messages.Operation):
      raise ValueError('result must be an Operation')

    resource_printer.Print(resources=result,
                           print_format=unused_args.format or 'yaml',
                           out=log.out)
