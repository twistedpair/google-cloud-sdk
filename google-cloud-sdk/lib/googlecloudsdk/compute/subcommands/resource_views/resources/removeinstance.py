# Copyright 2014 Google Inc. All Rights Reserved.

"""'resourceviews resources remove' command."""

from apiclient import errors
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties

from googlecloudsdk.shared.compute import rolling_updates_util as util


class RemoveInstance(base.Command):
  """Removes resources from a resource view by resource name."""

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
        help='A list of resource names to remove from the resource view.')

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
    project = properties.VALUES.core.project.Get(required=True)

    if args.region:
      raise exceptions.ToolException(ValueError(
          'addinstance must be used against a zonal resource view'))
    else:
      instance_urls = []
      for instance in args.resource:
        instance_urls.append(
            'https://www.googleapis.com/compute/v1/projects/' +
            project + '/zones/' + args.zone + '/instances/' +
            instance)
      request_body = {'resources': instance_urls}

    if 'v1beta1' in self.context['api_version']:
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
      log.Print('Instances removed from resource view {0}.'.format(
          args.resourceview))
    except errors.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))
    except errors.Error as error:
      raise exceptions.ToolException(error)

RemoveInstance.detailed_help = {
    'brief': 'Removes resources from a resource view by resource name.',
    'DESCRIPTION': """\
        This command removes resource from a resource view by resource name.
        The resource name will be converted to fully-qualified URLs before
        it is removed.

        This does not delete the actual resource but removes it from the view.
        """,
}
