# Copyright 2014 Google Inc. All Rights Reserved.

"""'resourceviews resources addinstance' command."""

from apiclient import errors
from googlecloudsdk.api_lib.compute import rolling_updates_util as util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties


class AddInstance(base.Command):
  """Adds resources to a resource view by resource name."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument(
        'resource',
        nargs='+',
        help='Resources to add to the resource view.')

  def Run(self, args):
    """Run 'resourceviews resources add'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Raises:
      HttpException: A http error response was received while executing api
          request.
      ToolException: An error other than http error occured while executing
          the command.
    """
    zone_views_client = self.context['zoneViewsClient']
    project = properties.VALUES.core.project.Get(required=True)

    if args.region:
      raise exceptions.ToolException(ValueError(
          'addinstance must be used against a zonal resourceview'))

    instance_urls = []
    for instance in args.resource:
      instance_urls.append(
          'https://www.googleapis.com/compute/v1/projects/' +
          project + '/zones/' + args.zone + '/instances/' +
          instance)
    request_body = {'resources': instance_urls}

    if 'v1beta1' in self.context['api_version']:
      request = zone_views_client.addresources(
          projectName=project,
          zone=args.zone,
          resourceViewName=args.resourceview,
          body=request_body)
    else:
      request = zone_views_client.addResources(
          project=project,
          zone=args.zone,
          resourceView=args.resourceview,
          body=request_body)

    try:
      request.execute()
      log.Print('Instances added to resource view {0}.'.format(
          args.resourceview))
    except errors.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))
    except errors.Error as error:
      raise exceptions.ToolException(error)

AddInstance.detailed_help = {
    'brief': 'Adds resources to a resource view by resource name.',
    'DESCRIPTION': """\
        This command adds resources to a resource view by resource name.
        The resource name will be converted to fully-qualified URLs before
        it is added.
        """,
}
