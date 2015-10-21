# Copyright 2014 Google Inc. All Rights Reserved.

"""resourceviews delete command."""

from apiclient import errors
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties

from googlecloudsdk.shared.compute import rolling_updates_util as util


class Delete(base.Command):
  """Delete a resource view."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument('name', nargs='+',
                        help='One or more resource view names.')

  def Run(self, args):
    """Run 'resourceviews delete'.

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

    for resourceview_name in args.name:
      if 'v1beta1' in self.context['api_version']:
        if args.region:
          request = region_views_client.delete(
              projectName=project,
              region=args.region,
              resourceViewName=resourceview_name)
        else:
          request = zone_views_client.delete(
              projectName=project,
              zone=args.zone,
              resourceViewName=resourceview_name)
      else:
        request = zone_views_client.delete(
            project=project,
            zone=args.zone,
            resourceView=resourceview_name)

      try:
        request.execute()
        log.Print('Resource view {0} deleted.'.format(resourceview_name))
      except errors.HttpError as error:
        raise exceptions.HttpException(util.GetError(error))
      except errors.Error as error:
        raise exceptions.ToolException(error)
