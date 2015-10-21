# Copyright 2015 Google Inc. All Rights Reserved.

"""Upgrade cluster command."""
import argparse

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.third_party.apitools.base import py as apitools_base

from googlecloudsdk.container.lib import api_adapter
from googlecloudsdk.container.lib import util


@base.ReleaseTracks(base.ReleaseTrack.GA)
class Upgrade(base.Command):
  """Upgrade the Kubernetes version of an existing container cluster."""

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
        help='The name of the cluster to upgrade.')
    cv = parser.add_argument(
        '--cluster-version',
        help='The Kubernetes release version to which to upgrade the'
        ' cluster\'s nodes. Omit to upgrade the nodes to the version the'
        ' cluster\'s Kubernetes master is running.')
    cv.detailed_help = """\
      The Kubernetes release version to which to upgrade the cluster's nodes.
      Omit to upgrade the nodes to the version the cluster's Kubernetes master
      is running.

      If provided, the --cluster-version must be no greater than the cluster
      master's minor version (x.*X*.x), and must be a latest patch version
      (x.x.*X*).

      You can find the current master version by running

        $ gcloud container clusters describe <cluster> | grep MasterVersion

      You can find the list of allowed node versions for upgrades by running

        $ gcloud container get-server-config

      and looking at the returned "validNodeVersions".
    """
    parser.add_argument(
        '--master',
        help=argparse.SUPPRESS,
        action='store_true')
    parser.add_argument(
        '--wait',
        action='store_true',
        default=True,
        help='Poll the operation for completion after issuing an upgrade '
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
        version=args.cluster_version,
        update_master=args.master,
        update_nodes=(not args.master))

    try:
      op_ref = adapter.UpdateCluster(cluster_ref, options)
    except apitools_base.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))

    if args.wait:
      adapter.WaitForOperation(
          op_ref, 'Upgrading {0}'.format(cluster_ref.clusterId))

      log.UpdatedResource(cluster_ref)

Upgrade.detailed_help = {
    'DESCRIPTION': """\
      Upgrades the Kubernetes version of an existing container cluster.

      This command upgrades the Kubernetes version of the *nodes* of a cluster.
      The Kubernetes version of the cluster's *master* is periodically upgraded
      automatically as new releases are available.

      *By running this command, all of the cluster's nodes will be deleted and*
      *recreated one at a time.* While persistent Kubernetes resources, such as
      pods backed by replication controllers, will be rescheduled onto new nodes,
      a small cluster may experience a few minutes where there are insufficient
      nodes available to run all of the scheduled Kubernetes resources.

      *Please ensure that any data you wish to keep is stored on a persistent*
      *disk before upgrading the cluster.* Ephemeral Kubernetes resources--in
      particular, pods without replication controllers--will be lost, while
      persistent Kubernetes resources will get rescheduled.
    """,
    'EXAMPLES': """\
      Upgrade the nodes of <cluster> to the Kubernetes version of the cluster's
      master.

        $ {command} <cluster>

      Upgrade the nodes of <cluster> to Kubernetes version x.y.z.

        $ {command} <cluster> --cluster-version "x.y.z"
    """,
}


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class UpgradeBeta(Upgrade):
  """Upgrade the Kubernetes version of an existing container cluster."""


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class UpgradeAlpha(Upgrade):
  """Upgrade the Kubernetes version of an existing container cluster."""
