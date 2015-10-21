# Copyright 2015 Google Inc. All Rights Reserved.

"""Fetch cluster credentials."""

from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core import properties

from googlecloudsdk.container.lib import util


class GetCredentials(base.Command):
  """Fetch credentials for a running cluster.

  See https://cloud.google.com/container-engine/docs/kubectl for
  kubectl documentation.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command.

    Args:
      parser: An argparse.ArgumentParser-like object. It is mocked out in order
          to capture some information, but behaves like an ArgumentParser.
    """
    parser.add_argument(
        'name',
        help='The name of the cluster to get credentials for.',
        action=actions.StoreProperty(properties.VALUES.container.cluster))

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Raises:
      util.Error: if the cluster is unreachable or not running.
    """
    util.CheckKubectlInstalled()
    adapter = self.context['api_adapter']
    cluster_ref = adapter.ParseCluster(args.name)

    log.status.Print('Fetching cluster endpoint and auth data.')
    # Call DescribeCluster to get auth info and cache for next time
    cluster = adapter.GetCluster(cluster_ref)
    if not adapter.IsRunning(cluster):
      log.error(
          'cluster %s is not running. The kubernetes API will probably be '
          'unreachable.' % cluster_ref.clusterId)
    util.ClusterConfig.Persist(cluster, cluster_ref.projectId, self.cli)
