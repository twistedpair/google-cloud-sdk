# Copyright 2015 Google Inc. All Rights Reserved.

"""Describe cluster command."""

from googlecloudsdk.calliope import base

from googlecloudsdk.dataproc.lib import util


class Describe(base.Command):
  """View the details of a cluster."""

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To view the details of a cluster, run:

            $ {command} my_cluster
          """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument('name', help='The name of the cluster to describe.')

  @util.HandleHttpError
  def Run(self, args):
    client = self.context['dataproc_client']

    cluster_ref = util.ParseCluster(args.name, self.context)
    request = cluster_ref.Request()

    cluster = client.projects_clusters.Get(request)
    return cluster

  def Display(self, args, result):
    self.format(result)
