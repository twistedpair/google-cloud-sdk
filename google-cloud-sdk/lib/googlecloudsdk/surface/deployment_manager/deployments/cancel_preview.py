# Copyright 2014 Google Inc. All Rights Reserved.

"""deployments cancel command."""

from googlecloudsdk.api_lib.deployment_manager import dm_v2_util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resource_printer
from googlecloudsdk.third_party.apitools.base import py as apitools_base


# Number of seconds (approximately) to wait for cancel operation to complete.
OPERATION_TIMEOUT = 20 * 60  # 20 mins


class CancelPreview(base.Command):
  """Cancel a pending or running deployment preview.

  This command will cancel a currently running or pending preview operation on
  a deployment.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To cancel a running operation on a deployment, run:

            $ {command} my-deployment

          To issue a cancel preview command without waiting for the operation to complete, run:

            $ {command} my-deployment --async
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

    parser.add_argument('deployment_name', help='Deployment name.')

  def Run(self, args):
    """Run 'deployments cancel-preview'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      If --async=true, returns Operation to poll.
      Else, returns boolean indicating whether cancel preview operation
      succeeded.

    Raises:
      HttpException: An http error response was received while executing api
          request.
      ToolException: The cancel preview operation encountered an error.
    """
    client = self.context['deploymentmanager-client']
    messages = self.context['deploymentmanager-messages']
    project = properties.VALUES.core.project.Get(required=True)

    # Get the fingerprint from the previewing deployment to cancel.
    try:
      current_deployment = client.deployments.Get(
          messages.DeploymentmanagerDeploymentsGetRequest(
              project=project,
              deployment=args.deployment_name
          )
      )
      # If no fingerprint is present, default to an empty fingerprint.
      # This empty default can be removed once the fingerprint change is
      # fully implemented and all deployments have fingerprints.
      fingerprint = current_deployment.fingerprint or ''
    except apitools_base.HttpError as error:
      raise exceptions.HttpException(dm_v2_util.GetError(error))

    try:
      operation = client.deployments.CancelPreview(
          messages.DeploymentmanagerDeploymentsCancelPreviewRequest(
              project=project,
              deployment=args.deployment_name,
              deploymentsCancelPreviewRequest=
              messages.DeploymentsCancelPreviewRequest(
                  fingerprint=fingerprint,
              ),
          )
      )
    except apitools_base.HttpError as error:
      raise exceptions.HttpException(dm_v2_util.GetError(error))
    if args.async:
      return operation
    else:
      op_name = operation.name
      try:
        dm_v2_util.WaitForOperation(op_name, project, self.context,
                                    'cancel-preview', OPERATION_TIMEOUT)
        log.status.Print('Cancel preview operation ' + op_name
                         + ' completed successfully.')
      except exceptions.ToolException:
        # Operation timed out or had errors. Print this warning, then still
        # show whatever operation can be gotten.
        log.error('Cancel preview operation ' + op_name
                  + ' has errors or failed to complete within '
                  + str(OPERATION_TIMEOUT) + ' seconds.')
      except apitools_base.HttpError as error:
        raise exceptions.HttpException(dm_v2_util.GetError(error))
      try:
        # Fetch a list of the canceled resources.
        response = client.resources.List(
            messages.DeploymentmanagerResourcesListRequest(
                project=project,
                deployment=args.deployment_name,
            )
        )
        # TODO(munutzer): Pagination
        return response.resources if response.resources else []
      except apitools_base.HttpError as error:
        raise exceptions.HttpException(dm_v2_util.GetError(error))

  def Display(self, unused_args, result):
    """Display prints information about what just happened to stdout.

    Args:
      unused_args: The same as the args in Run.

      result: an Operation (may be in progress or completed) to display
          or a list of Resources, if a synchronous cancel preview completed
          successfully.

    Raises:
      ValueError: if result is None or not a dict
    """
    messages = self.context['deploymentmanager-messages']
    if isinstance(result, messages.Operation):
      resource_printer.Print(resources=result,
                             print_format=unused_args.format or 'yaml',
                             out=log.out)
    elif isinstance(result, list) and (
        not result or isinstance(result[0], messages.Resource)):
      list_printer.PrintResourceList('deploymentmanagerv2.resources',
                                     result)
    else:
      raise ValueError('result must be an Operation or list of Resources')

