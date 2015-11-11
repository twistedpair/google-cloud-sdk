# Copyright 2014 Google Inc. All Rights Reserved.

"""replicapool update-template command."""

from apiclient import errors
from googlecloudsdk.api_lib.compute import replica_template_util
from googlecloudsdk.api_lib.compute import rolling_updates_util as util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties


class UpdateTemplate(base.Command):
  """Updates the template for an existing replica pool."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument('pool', help='Replica pool name.')
    parser.add_argument(
        '--template', required=True,
        help=('Path to YAML or JSON file containing the new replica pool '
              'template.'))
    replica_template_util.AddTemplateParamArgs(parser)

  def Run(self, args):
    """Run 'replicapool update-template'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      An object representing the service response obtained by the Get
      API if the Get call was successful.

    Raises:
      HttpException: A http error response was received while executing api
          request.
      ToolException: An error other than http error occured while executing
          the command.
    """
    client = self.context['replicapool']
    project = properties.VALUES.core.project.Get(required=True)

    template = replica_template_util.ParseTemplate(
        args.template, params=args.param, params_from_file=args.param_from_file)

    request = client.pools().updatetemplate(
        projectName=project,
        zone=args.zone,
        poolName=args.pool,
        body=template['template'])

    try:
      request.execute()
      log.Print('Template updated for replica pool {0}.'.format(args.pool))
    except errors.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))
    except errors.Error as error:
      raise exceptions.ToolException(error)

UpdateTemplate.detailed_help = {
    'brief': 'Updates the template for an existing replica pool.',
    'DESCRIPTION': """\
        This command updates the template for an existing replica pool.

        The new template won't apply to existing replicas unless they are
        restarted but applies to all new replicas added to the replica pool.
        """,
}
