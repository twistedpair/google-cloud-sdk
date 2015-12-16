# Copyright 2014 Google Inc. All Rights Reserved.

"""deployments delete command."""

from googlecloudsdk.api_lib.deployment_manager import dm_v2_util
from googlecloudsdk.api_lib.deployment_manager.exceptions import DeploymentManagerError
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resource_printer
from googlecloudsdk.core.console import console_io
from googlecloudsdk.third_party.apitools.base.py import exceptions as apitools_exceptions

# Number of seconds (approximately) to wait for each delete operation to
# complete.
OPERATION_TIMEOUT = 20 * 60  # 20 mins


class Delete(base.Command):
  """Delete a deployment.

  This command deletes a deployment and deletes all associated resources.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To delete a deployment, run:

            $ {command} my-deployment

          To issue a delete command without waiting for the operation to complete, run:

            $ {command} my-deployment --async

          To delete several deployments, run:

            $ {command} deployment-one deployment-two deployment-three

          To disable the confirmation prompt on delete, run:

            $ {command} my-deployment -q
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
    parser.add_argument(
        '--async',
        help='Return immediately and print information about the Operation in '
        'progress rather than waiting for the Operation to complete. '
        '(default=False)',
        dest='async',
        default=False,
        action='store_true')
    parser.add_argument('deployment_name', nargs='+', help='Deployment name.')

  def Run(self, args):
    """Run 'deployments delete'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      If --async=true, returns Operation to poll.
      Else, returns boolean indicating whether insert operation succeeded.

    Raises:
      HttpException: An http error response was received while executing api
          request.
      ToolException: The deployment deletion operation encountered an error.
    """
    client = self.context['deploymentmanager-client']
    messages = self.context['deploymentmanager-messages']
    project = properties.VALUES.core.project.Get(required=True)

    prompt_message = ('The following deployments will be deleted:\n- '
                      + '\n- '.join(args.deployment_name))
    if not args.quiet:
      if not console_io.PromptContinue(message=prompt_message, default=False):
        raise exceptions.ToolException('Deletion aborted by user.')

    operations = []
    for deployment_name in args.deployment_name:
      try:
        operation = client.deployments.Delete(
            messages.DeploymentmanagerDeploymentsDeleteRequest(
                project=project,
                deployment=deployment_name,
            )
        )
      except apitools_exceptions.HttpError as error:
        raise exceptions.HttpException(dm_v2_util.GetError(error))
      if args.async:
        operations.append(operation)
      else:
        op_name = operation.name
        try:
          dm_v2_util.WaitForOperation(op_name, project, self.context, 'delete',
                                      OPERATION_TIMEOUT)
          log.status.Print('Delete operation ' + op_name
                           + ' completed successfully.')
        except (exceptions.ToolException, DeploymentManagerError):
          log.error('Delete operation ' + op_name
                    + ' has errors or failed to complete within in '
                    + str(OPERATION_TIMEOUT) + ' seconds.')
        except apitools_exceptions.HttpError as error:
          raise exceptions.HttpException(dm_v2_util.GetError(error))
        try:
          completed_operation = client.operations.Get(
              messages.DeploymentmanagerOperationsGetRequest(
                  project=project,
                  operation=op_name,
              )
          )
        except apitools_exceptions.HttpError as error:
          raise exceptions.HttpException(dm_v2_util.GetError(error))
        operations.append(completed_operation)

    return operations

  def Display(self, unused_args, result):
    """Display prints information about what just happened to stdout.

    Args:
      unused_args: The same as the args in Run.

      result: a list of delete operations

    Raises:
      ValueError: if result is None or not a list
    """
    if not isinstance(result, list):
      raise ValueError('result must be a list')

    resource_printer.Print(resources=result,
                           print_format=unused_args.format or 'yaml',
                           out=log.out)
