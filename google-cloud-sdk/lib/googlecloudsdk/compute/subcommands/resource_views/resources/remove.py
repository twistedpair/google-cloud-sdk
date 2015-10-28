# Copyright 2014 Google Inc. All Rights Reserved.

"""'resourceviews resources remove' command."""


from apiclient import errors
from googlecloudsdk.api_lib.compute import rolling_updates_util as util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties


class Remove(base.Command):
  """Remove resources from a resource view."""

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
        help=('A list of fully-qualified URLs to remove from a resource view. '
              'For example:  https://www.googleapis.com/compute/v1/projects/'
              'myproject/zones/us-central1-a/instances/instance-1'))

  def Run(self, args):
    """Run 'resourceviews resources remove'.

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
        request = region_views_client.removeresources(
            projectName=project,
            region=args.region,
            resourceViewName=args.resourceview,
            body=request_body)
      else:
        request = zone_views_client.removeresources(
            projectName=project,
            zone=args.zone,
            resourceViewName=args.resourceview,
            body=request_body)
    else:
      request = zone_views_client.removeResources(
          project=project,
          zone=args.zone,
          resourceView=args.resourceview,
          body=request_body)

    try:
      request.execute()
      log.Print('Resources removed from resource view {0}.'.format(
          args.resourceview))
    except errors.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))
    except errors.Error as error:
      raise exceptions.ToolException(error)

Remove.detailed_help = {
    'brief': 'Remove resources from a resource view.',
    'DESCRIPTION': """\
        This command removes resources from a resource view. This does not
        delete any resources but simply removes them from this view.

        You must provide a list of fully-qualified URLs to each resource if
        you use this command. Alternatively, you can also use the
        removeinstance command and provide resources by name.
        """,
}
