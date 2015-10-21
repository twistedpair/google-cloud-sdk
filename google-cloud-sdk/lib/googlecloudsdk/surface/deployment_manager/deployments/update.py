# Copyright 2014 Google Inc. All Rights Reserved.

"""deployments update command."""

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resource_printer
from googlecloudsdk.shared.deployment_manager import dm_v2_util
from googlecloudsdk.shared.deployment_manager import importer
from googlecloudsdk.third_party.apis.deploymentmanager.v2 import deploymentmanager_v2_messages as v2_messages
from googlecloudsdk.third_party.apitools.base import py as apitools_base

# Number of seconds (approximately) to wait for update operation to complete.
OPERATION_TIMEOUT = 20 * 60  # 20 mins


class Update(base.Command):
  """Update a deployment based on a provided config file.

  This command will update a deployment with the new config file provided.
  Different policies for create, update, and delete policies can be specified.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To update an existing deployment with a new config file, run:

            $ {command} my-deployment --config new_config.yaml

          To preview an update to an existing deployment without actually modifying the resources, run:

            $ {command} my-deployment --config new_config.yaml --preview

          To apply an update that has been previewed, provide the name of the previewed deployment, and no config file:

            $ {command} my-deployment

          To specify different create, update, or delete policies, include any subset of the following flags;

            $ {command} my-deployment --config new_config.yaml --create-policy ACQUIRE --delete-policy ABANDON

          To perform an update without waiting for the operation to complete, run:

            $ {command} my-deployment --config new_config.yaml --async
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

    parser.add_argument(
        '--config',
        help='Filename of config which specifies resources to deploy. '
        'Required unless launching an already-previewed update to this '
        'deployment.',
        dest='config')

    parser.add_argument(
        '--properties',
        type=arg_parsers.ArgDict(),
        help='A comma seperated, key=value, map '
        'to be used when deploying a template file directly.',
        dest='properties')

    parser.add_argument(
        '--preview',
        help='Preview the requested update without making any changes to the'
        'underlying resources. (default=False)',
        dest='preview',
        default=False,
        action='store_true')

    parser.add_argument(
        '--create-policy',
        help='Create policy for resources that have changed in the update. '
        'Can be CREATE_OR_ACQUIRE (default) or ACQUIRE.',
        dest='create_policy',
        default='CREATE_OR_ACQUIRE',
        choices=(v2_messages.DeploymentmanagerDeploymentsUpdateRequest
                 .CreatePolicyValueValuesEnum.to_dict().keys()))

    parser.add_argument(
        '--delete-policy',
        help='Delete policy for resources that have changed in the update. '
        'Can be DELETE (default) or ABANDON.',
        dest='delete_policy',
        default='DELETE',
        choices=(v2_messages.DeploymentmanagerDeploymentsUpdateRequest
                 .DeletePolicyValueValuesEnum.to_dict().keys()))

  def Run(self, args):
    """Run 'deployments update'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      If --async=true, returns Operation to poll.
      Else, returns boolean indicating whether update operation succeeded.

    Raises:
      HttpException: An http error response was received while executing api
          request.
      ToolException: Config file could not be read or parsed, or the deployment
          creation operation encountered an error.
    """
    client = self.context['deploymentmanager-client']
    messages = self.context['deploymentmanager-messages']
    project = properties.VALUES.core.project.Get(required=True)

    deployment = messages.Deployment(
        name=args.deployment_name,
    )
    if args.config:
      deployment.target = importer.BuildTargetConfig(
          messages, args.config, args.properties)
    # Get the fingerprint from the deployment to update.
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
      deployment.fingerprint = current_deployment.fingerprint or ''
    except apitools_base.HttpError as error:
      raise exceptions.HttpException(dm_v2_util.GetError(error))

    try:
      operation = client.deployments.Update(
          messages.DeploymentmanagerDeploymentsUpdateRequest(
              deploymentResource=deployment,
              project=project,
              deployment=args.deployment_name,
              preview=args.preview,
              createPolicy=(messages.DeploymentmanagerDeploymentsUpdateRequest
                            .CreatePolicyValueValuesEnum(args.create_policy)),
              deletePolicy=(messages.DeploymentmanagerDeploymentsUpdateRequest
                            .DeletePolicyValueValuesEnum(args.delete_policy)),
          )
      )
    except apitools_base.HttpError as error:
      raise exceptions.HttpException(dm_v2_util.GetError(error))
    if args.async:
      return operation
    else:
      op_name = operation.name
      try:
        dm_v2_util.WaitForOperation(op_name, project, self.context, 'update',
                                    OPERATION_TIMEOUT)
        log.status.Print('Update operation ' + op_name
                         + ' completed successfully.')
      except exceptions.ToolException:
        # Operation timed out or had errors. Print this warning, then still
        # show whatever operation can be gotten.
        log.error('Update operation ' + op_name
                  + ' has errors or failed to complete within '
                  + str(OPERATION_TIMEOUT) + ' seconds.')
      except apitools_base.HttpError as error:
        raise exceptions.HttpException(dm_v2_util.GetError(error))
      try:
        # Fetch a list of the previewed or updated resources.
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
          or a list of Resources, if a synchronous preview completed.

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

