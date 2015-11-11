# Copyright 2014 Google Inc. All Rights Reserved.

"""The command-group for the Replica Pool service CLI."""

from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.credentials import store


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class Replicapool(base.Group):
  """Manage cloud replica pools.

  This command group manages cloud replica pools.

  Replica pools have been replaced by instance groups; please use those instead.
  """

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument(
        '--zone', required=True, help='Replica pool zone name',
        action=actions.StoreProperty(properties.VALUES.compute.zone))

  @exceptions.RaiseToolExceptionInsteadOf(store.Error)
  def Filter(self, context, args):
    """Context() is a filter function that can update the context.

    Args:
      context: The current context.
      args: The argparse namespace that was specified on the CLI or API.

    Returns:
      The updated context.
    """
    # pylint:disable=g-import-not-at-top, Delaying import for performance.
    import apiclient.discovery as discovery

    # Create the Replica Pool service client
    api_server = properties.VALUES.core.api_host.Get()
    # Re-using the compute API overrides from compute, which is not technically
    # correct (since this is a different API), but we don't want to introduce
    # another property only to remove it.
    api_version = (properties.VALUES.api_client_overrides.compute.Get() or
                   'v1beta1')

    discovery_url = ('{server}/discovery/v1/apis/replicapool/{version}/rest'
                     .format(server=api_server.rstrip('/'),
                             version=api_version))
    http = self.Http()
    client = discovery.build(
        'replicapool', api_version, http=http,
        discoveryServiceUrl=discovery_url)
    context['replicapool'] = client

    return context
