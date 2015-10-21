# Copyright 2015 Google Inc. All Rights Reserved.

"""Update cluster command."""

import argparse

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log

from googlecloudsdk.dataproc.lib import util


class Update(base.Command):
  """Update the number of worker nodes in a cluster."""

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To resize a cluster, run:

            $ {command} my_cluster --num-workers 5

          To change the number preemptible workers in a cluster, run:

            $ {command} my_cluster --num-preemptible-workers 5
          """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'name',
        help='The name of the cluster to update.')
    parser.add_argument(
        '--num-workers',
        type=int,
        help='The new number of worker nodes in the cluster.')
    parser.add_argument(
        '--num-preemptible-workers',
        type=int,
        help='The new number of preemptible worker nodes in the cluster.')
    # Leaving this option here since it was in public announcement.
    # Hiding it so new users see the preferred --num-workers
    # option in help.
    # TODO(user): remove before public beta launch.
    parser.add_argument(
        '--new-num-workers',
        type=int,
        help=argparse.SUPPRESS)

  @util.HandleHttpError
  def Run(self, args):
    client = self.context['dataproc_client']
    messages = self.context['dataproc_messages']

    cluster_ref = util.ParseCluster(args.name, self.context)

    cluster_config = messages.ClusterConfiguration()
    changed_fields = []

    has_changes = False

    if args.new_num_workers is not None:
      log.warn('--new-num-workers parameter is deprecated and will be removed '
               'in a future release. Please use --num-workers instead')
      args.num_workers = args.new_num_workers

    if args.num_workers is not None:
      worker_config = messages.InstanceGroupConfiguration(
          numInstances=args.num_workers)
      cluster_config.workerConfiguration = worker_config
      changed_fields.append('configuration.worker_configuration.num_instances')
      has_changes = True

    if args.num_preemptible_workers is not None:
      worker_config = messages.InstanceGroupConfiguration(
          numInstances=args.num_preemptible_workers)
      cluster_config.secondaryWorkerConfiguration = worker_config
      changed_fields.append(
          'configuration.secondary_worker_configuration.num_instances')
      has_changes = True

    if not has_changes:
      raise exceptions.ToolException(
          'Must specify at least one cluster parameter to update.')

    cluster = messages.Cluster(
        configuration=cluster_config,
        clusterName=cluster_ref.clusterName,
        projectId=cluster_ref.projectId)

    request = messages.DataprocProjectsClustersPatchRequest(
        clusterName=cluster_ref.clusterName,
        projectId=cluster_ref.projectId,
        cluster=cluster,
        updateMask=','.join(changed_fields))

    operation = client.projects_clusters.Patch(request)
    util.WaitForOperation(
        operation,
        self.context,
        message='Waiting for cluster update operation',
        timeout_s=3600 * 3)

    cluster = client.projects_clusters.Get(cluster_ref.Request())
    log.UpdatedResource(cluster_ref)
    return cluster

  def Display(self, args, result):
    self.format(result)
