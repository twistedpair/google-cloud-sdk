# Copyright 2015 Google Inc. All Rights Reserved.

"""bigtable clusters list command."""


from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io as io
from googlecloudsdk.shared.bigtable import util


class ListClusters(base.Command):
  """List existing Bigtable clusters."""

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    pass

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
           BigtableclusteradminProjectsAggregatedClustersListRequest(
               name=util.ProjectUrl()))
    return cli.projects_aggregated_clusters.List(msg)

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    tbl = io.TablePrinter(
        ['Name', 'ID', 'Zone', 'Nodes'],
        justification=tuple(
            [io.TablePrinter.JUSTIFY_LEFT] * 3 +
            [io.TablePrinter.JUSTIFY_RIGHT]))
    values = [TableValues(cluster) for cluster in result.clusters]
    tbl.Print(values)
    if not values:
      log.err.Print('0 clusters')


def TableValues(cluster):
  """Converts a cluster dict into a tuple of column values."""
  zone_id, cluster_id = util.ExtractZoneAndCluster(cluster.name)
  return (cluster.displayName,
          cluster_id,
          zone_id,
          str(cluster.serveNodes))

