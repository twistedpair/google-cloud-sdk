# Copyright 2014 Google Inc. All Rights Reserved.

"""deployments create command."""

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resource_printer
from googlecloudsdk.shared.deployment_manager import dm_v2_util
from googlecloudsdk.shared.deployment_manager import importer
from googlecloudsdk.third_party.apitools.base import py as apitools_base

# Number of seconds (approximately) to wait for create operation to complete.
OPERATION_TIMEOUT = 20 * 60  # 20 mins


class Create(base.Command):
  """Create a deployment.

  This command inserts (creates) a new deployment based on a provided config
  file.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To create a new deployment, run:

            $ {command} my-deployment --config config.yaml --description "My deployment"

          To preview a deployment without actually creating resources, run:

            $ {command} my-new-deployment --config config.yaml --preview

          To instantiate a deployment that has been previewed, issue an update command for that deployment without specifying a config file.
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
        help='Filename of config which specifies resources to deploy.',
        dest='config',
        required=True)

    parser.add_argument(
        '--properties',
        type=arg_parsers.ArgDict(),
        help='A comma seperated, key=value, map '
        'to be used when deploying a template file directly.',
        dest='properties')

    parser.add_argument(
        '--description',
        help='Optional description of the deployment to insert.',
        dest='description')

    parser.add_argument(
        '--preview',
        help='Preview the requested create without actually instantiating the '
        'underlying resources. (default=False)',
        dest='preview',
        default=False,
        action='store_true')

  def Run(self, args):
    """Run 'deployments create'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      If --async=true, returns Operation to poll.
      Else, returns boolean indicating whether create operation succeeded.

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
        target=importer.BuildTargetConfig(
            messages, args.config, args.properties),
    )
    if args.description:
      deployment.description = args.description

    try:
      operation = client.deployments.Insert(
          messages.DeploymentmanagerDeploymentsInsertRequest(
              project=project,
              deployment=deployment,
              preview=args.preview,
          )
      )
    except apitools_base.HttpError as error:
      raise exceptions.HttpException(dm_v2_util.GetError(error))
    if args.async:
      return operation
    else:
      op_name = operation.name
      try:
        dm_v2_util.WaitForOperation(op_name, project, self.context, 'create',
                                    OPERATION_TIMEOUT)
        log.status.Print('Create operation ' + op_name
                         + ' completed successfully.')
      except exceptions.ToolException:
        # Operation timed out or had errors. Print this warning, then still
        # show whatever operation can be gotten.
        log.error('Create operation ' + op_name
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
        or a list of Resources, if a synchronous preview or create completed.

    Raises:
      ValueError: if result is not a list of Resources or an Operation
    """
    messages = self.context['deploymentmanager-messages']
    if isinstance(result, messages.Operation):
      resource_printer.Print(resources=result,
                             print_format=unused_args.format or 'yaml',
                             out=log.out)
    elif isinstance(result, list) and not result:
      log.Print('No Deployments were found in your project!')
    elif isinstance(result, list) and isinstance(result[0], messages.Resource):
      list_printer.PrintResourceList('deploymentmanagerv2.resources',
                                     result)
    else:
      raise ValueError('result must be an Operation or list of Resources')
