# Copyright 2015 Google Inc. All Rights Reserved.

"""bigtable clusters delete command."""

from googlecloudsdk.api_lib.bigtable import util
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log


class DeleteCluster(base.Command):
  """Delete a Bigtable cluster (along with all its data)."""

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    util.AddClusterIdArgs(parser)

  @util.MapHttpError
  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      Some value that we want to have printed later.
    """
    cli = self.context['clusteradmin']
    msg = (self.context['clusteradmin-msgs'].
           BigtableclusteradminProjectsZonesClustersDeleteRequest(
               name=util.ClusterUrl(args)))
    return cli.projects_zones_clusters.Delete(msg)

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    # Always use this log module for printing (never use print directly).
    # This allows us to control the verbosity of commands in a global way.
    writer = log.out
    writer.Print('Cluster [{0}] in zone [{1}] marked for deletion.'.format(
        args.cluster, args.zone))

