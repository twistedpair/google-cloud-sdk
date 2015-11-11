# Copyright 2014 Google Inc. All Rights Reserved.

"""'resourceviews resources add' command."""

from apiclient import errors
from googlecloudsdk.api_lib.compute import rolling_updates_util as util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties


class Add(base.Command):
  """Add resources to a resource view."""

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
        help=('A list of fully-qualified URLs to each resource that should '
              'be added to this view. For example: '
              'https://www.googleapis.com/compute/v1/projects/myproject/'
              'zones/us-central1-a/instances/instance-1'))

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
    region_views_client = self.context['regionViewsClient']

    project = properties.VALUES.core.project.Get(required=True)

    request_body = {'resources': args.resource}
    if 'v1beta1' in self.context['api_version']:
      if args.region:
        request = region_views_client.addresources(
            projectName=project,
            region=args.region,
            resourceViewName=args.resourceview,
            body=request_body)
      else:
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
      log.Print('Resources added to resource view {0}.'.format(
          args.resourceview))
    except errors.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))
    except errors.Error as error:
      raise exceptions.ToolException(error)

Add.detailed_help = {
    'brief': 'Add resources to a resource view.',
    'DESCRIPTION': """\
        This command adds resources to a resource view. You must provide a
        list of fully-qualified URLs for each resource.

        Alternatively, you can also use the addinstances command and provide
        resource names rather than URLs.
        """,
}
