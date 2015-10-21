# Copyright 2015 Google Inc. All Rights Reserved.

"""Update cluster command."""
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.third_party.apitools.base import py as apitools_base

from googlecloudsdk.container.lib import api_adapter
from googlecloudsdk.container.lib import util


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class Update(base.Command):
  """Update cluster settings for an existing container cluster."""

  @staticmethod
  def Args(parser):
    """Register flags for this command.

    Args:
      parser: An argparse.ArgumentParser-like object. It is mocked out in order
          to capture some information, but behaves like an ArgumentParser.
    """
    parser.add_argument(
        'name',
        metavar='NAME',
        help='The name of the cluster to update.')
    parser.add_argument(
        '--monitoring-service',
        dest='monitoring_service',
        required=True,
        help='The monitoring service to use for the cluster. Options '
        'are: "monitoring.googleapis.com" (the Google Cloud Monitoring '
        'service),  "none" (no metrics will be exported from the cluster)')
    parser.add_argument(
        '--wait',
        action='store_true',
        default=True,
        help='Poll the operation for completion after issuing an update '
        'request.')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      Some value that we want to have printed later.
    """
    adapter = self.context['api_adapter']

    cluster_ref = adapter.ParseCluster(args.name)

    # Make sure it exists (will raise appropriate error if not)
    adapter.GetCluster(cluster_ref)

    options = api_adapter.UpdateClusterOptions(
        update_cluster=True,
        monitoring_service=args.monitoring_service)

    try:
      op_ref = adapter.UpdateCluster(cluster_ref, options)
    except apitools_base.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))

    if args.wait:
      adapter.WaitForOperation(
          op_ref, 'Updating {0}'.format(cluster_ref.clusterId))

      log.UpdatedResource(cluster_ref)
