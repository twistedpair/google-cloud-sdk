# Copyright 2014 Google Inc. All Rights Reserved.

"""The super-group for the Resource Views CLI."""

from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.credentials import store


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class ResourceViews(base.Group):
  """Manage Cloud Resource Views."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument(
        '--zone',
        required=False,
        help='Resource view zone name.',
        action=actions.StoreProperty(properties.VALUES.compute.zone))
    parser.add_argument(
        '--region',
        required=False,
        help='Resource view region name.',
        action=actions.StoreProperty(properties.VALUES.compute.region))
    # TODO(user): Debug and add a mutually exclusive argument group so that
    # zone and region are not set together, but exactly one of them is set.

  @exceptions.RaiseToolExceptionInsteadOf(store.Error)
  def Filter(self, context, args):
    """Context() is a filter function that can update the context.

    Args:
      context: The current context.
      args: The argparse namespace that was specified on the CLI or API.
    Raises:
      ToolException: if the zone or region flags are provided together or
        are not provided at all.
    Returns:
      The updated context.
    """
    # pylint:disable=g-import-not-at-top, Delaying import for performance.
    import apiclient.discovery as discovery

    api_server = properties.VALUES.core.api_host.Get()
    # Re-using the compute API overrides from compute, which is not technically
    # correct (since this is a different API), but we don't want to introduce
    # another property only to remove it.
    api_version = (properties.VALUES.api_client_overrides.compute.Get() or
                   'v1beta1')
    context['api_version'] = api_version

    discovery_url = ('{server}/discovery/v1/apis/resourceviews/{version}/rest'
                     .format(server=api_server.rstrip('/'),
                             version=api_version))
    http = self.Http()
    client = discovery.build(
        'resourceviews', api_version, http=http,
        discoveryServiceUrl=discovery_url)

    zone_views_client = client.zoneViews()

    # TODO(user): Remove when v1beta1 is deprecated.
    # Alias the API names so that we can continue to support v1beta1
    context['regionViewsClient'] = None
    if 'v1beta1' in api_version:
      region_views_client = client.regionViews()
      context['regionViewsClient'] = region_views_client
      if args.region and args.zone:
        raise exceptions.ToolException(
            '--zone and --region flags must not be set together!')
      if not (args.region or args.zone):
        raise exceptions.ToolException(
            'either --zone or --region must be set!')
    else:
      if not args.zone:
        raise exceptions.ToolException(
            '--zone is required and must be provided for all v1beta2 commands')

    context['zoneViewsClient'] = zone_views_client

    return context
