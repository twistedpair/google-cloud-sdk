# Copyright 2014 Google Inc. All Rights Reserved.

"""resourceviews get command."""


from apiclient import errors
from googlecloudsdk.api_lib.compute import rolling_updates_util as util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import properties


class Get(base.Command):
  """Gets information about a single resource view."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument('name', help='Resource view name')

  def Run(self, args):
    """Run 'resourceviews get'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      The object representing the resource views.

    Raises:
      HttpException: A http error response was received while executing api
          request.
      ToolException: An error other than http error occured while executing
          the command.
    """
    zone_views_client = self.context['zoneViewsClient']
    region_views_client = self.context['regionViewsClient']

    project = properties.VALUES.core.project.Get(required=True)

    if 'v1beta1' in self.context['api_version']:
      if args.region:
        request = region_views_client.get(
            projectName=project, region=args.region,
            resourceViewName=args.name)
      else:
        request = zone_views_client.get(
            projectName=project, zone=args.zone,
            resourceViewName=args.name)
    else:
      request = zone_views_client.get(
          project=project, zone=args.zone, resourceView=args.name)

    try:
      response = request.execute()
      if not args.format:
        util.PrettyPrint(response, 'yaml')
      return response
    except errors.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))
    except errors.Error as error:
      raise exceptions.ToolException(error)

Get.detailed_help = {
    'brief': 'Gets information about a single resource view.',
    'DESCRIPTION': """\
        This command gets information about a single resource view.

        By default, this information is displayed in yaml format.
        You can also specify json or text formats.
        """,
}
