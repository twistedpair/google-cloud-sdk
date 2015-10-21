# Copyright 2014 Google Inc. All Rights Reserved.

"""resourceviews create command."""

from apiclient import errors
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties

from googlecloudsdk.shared.compute import rolling_updates_util as util


class Create(base.Command):
  """Insert (create) a resource view."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument('name', help='Resource view name.')
    parser.add_argument('--description', help='Description for the view.')

  def Run(self, args):
    """Run 'resourceviews create'.

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
    # remove the regional service client when v1beta1 is deprecated.
    region_views_client = self.context['regionViewsClient']

    project = properties.VALUES.core.project.Get(required=True)

    new_resourceview = {
        'name': args.name,
        'description': args.description,
    }

    if 'v1beta1' in self.context['api_version']:
      if args.region:
        request = region_views_client.insert(
            projectName=project, region=args.region, body=new_resourceview)
      else:
        request = zone_views_client.insert(
            projectName=project, zone=args.zone, body=new_resourceview)
    else:
      request = zone_views_client.insert(
          project=project, zone=args.zone, body=new_resourceview)

    try:
      request.execute()
      log.Print('Resource view {0} created.'.format(args.name))
    except errors.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))
    except errors.Error as error:
      raise exceptions.ToolException(error)
