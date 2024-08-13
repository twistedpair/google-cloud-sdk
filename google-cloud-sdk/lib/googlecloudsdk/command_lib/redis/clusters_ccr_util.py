# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Utility for Memorystore Redis clusters Cross Cluster Replication."""

from googlecloudsdk.command_lib.redis import util
from googlecloudsdk.core import exceptions


class DetachNotSupportedException(exceptions.Error):
  """Exception for when detach is not supported."""


class SwitchoverNotSupportedException(exceptions.Error):
  """Exception for when switchover is not supported."""


class DetachSecondariesNotSupportedException(exceptions.Error):
  """Exception for when detach-secondaries is not supported."""


def _GetCluster(cluster_ref, cluster_name):
  client = util.GetClientForResource(cluster_ref)
  messages = util.GetMessagesForResource(cluster_ref)
  return client.projects_locations_clusters.Get(
      messages.RedisProjectsLocationsClustersGetRequest(name=cluster_name)
  )


def Switchover(cluster_ref, args, patch_request):
  """Hook to trigger the switchover to the secondary cluster."""
  del args
  cluster = _GetCluster(cluster_ref, patch_request.name)
  messages = util.GetMessagesForResource(cluster_ref)
  if (
      cluster.crossClusterReplicationConfig is None
      or cluster.crossClusterReplicationConfig.clusterRole
      != (
          messages.CrossClusterReplicationConfig.ClusterRoleValueValuesEnum.SECONDARY
      )
  ):
    raise SwitchoverNotSupportedException(
        'Cluster {} is not a secondary cluster. Please run switchover on a'
        ' secondary cluster.'.format(cluster.name)
    )

  # The current primary cluster will become a secondary cluster.
  new_secondary_clusters = [
      messages.RemoteCluster(
          cluster=cluster.crossClusterReplicationConfig.primaryCluster.cluster
      )
  ]
  # Add the rest of the secondary clusters to the new secondary clusters list.
  for (
      curr_sec_cluster
  ) in cluster.crossClusterReplicationConfig.membership.secondaryClusters:
    # Filter out the current cluster from the secondary clusters list.
    if curr_sec_cluster.cluster != cluster.name:
      new_secondary_clusters.append(
          messages.RemoteCluster(cluster=curr_sec_cluster.cluster)
      )

  new_ccr_config = messages.CrossClusterReplicationConfig(
      clusterRole=messages.CrossClusterReplicationConfig.ClusterRoleValueValuesEnum.PRIMARY,
      secondaryClusters=new_secondary_clusters,
  )

  patch_request.updateMask = 'cross_cluster_replication_config'
  patch_request.cluster = messages.Cluster(
      crossClusterReplicationConfig=new_ccr_config
  )
  return patch_request


def Detach(cluster_ref, args, patch_request):
  """Hook to detach the secondary cluster from the primary cluster."""
  del args
  cluster = _GetCluster(cluster_ref, patch_request.name)
  messages = util.GetMessagesForResource(cluster_ref)
  if (
      cluster.crossClusterReplicationConfig is None
      or cluster.crossClusterReplicationConfig.clusterRole
      != (
          messages.CrossClusterReplicationConfig.ClusterRoleValueValuesEnum.SECONDARY
      )
  ):
    raise DetachNotSupportedException(
        'Cluster {} is not a secondary cluster. Please run detach on a'
        ' secondary cluster.'.format(cluster.name)
    )

  new_ccr_config = messages.CrossClusterReplicationConfig(
      clusterRole=messages.CrossClusterReplicationConfig.ClusterRoleValueValuesEnum.NONE
  )

  patch_request.updateMask = 'cross_cluster_replication_config'
  patch_request.cluster = messages.Cluster(
      crossClusterReplicationConfig=new_ccr_config
  )
  return patch_request


def DetachSecondaries(cluster_ref, args, patch_request):
  """Hook to detach the given secondary clusters from the primary cluster."""
  cluster = _GetCluster(cluster_ref, patch_request.name)
  messages = util.GetMessagesForResource(cluster_ref)
  if (
      cluster.crossClusterReplicationConfig is None
      or cluster.crossClusterReplicationConfig.clusterRole
      != (
          messages.CrossClusterReplicationConfig.ClusterRoleValueValuesEnum.PRIMARY
      )
  ):
    raise DetachSecondariesNotSupportedException(
        'Cluster {} is not a primary cluster. Please run detach-secondaries on'
        ' a primary cluster.'.format(cluster.name)
    )

  current_secondary_clusters = (
      cluster.crossClusterReplicationConfig.secondaryClusters
  )
  new_secondary_clusters = []
  for secondary_cluster in current_secondary_clusters:
    if secondary_cluster.cluster not in args.clusters_to_detach:
      new_secondary_clusters.append(secondary_cluster)

  new_ccr_config = messages.CrossClusterReplicationConfig()
  if not new_secondary_clusters:
    new_ccr_config.clusterRole = (
        messages.CrossClusterReplicationConfig.ClusterRoleValueValuesEnum.NONE
    )
  else:
    new_ccr_config.clusterRole = (
        messages.CrossClusterReplicationConfig.ClusterRoleValueValuesEnum.PRIMARY
    )
    new_ccr_config.secondaryClusters = new_secondary_clusters

  patch_request.updateMask = 'cross_cluster_replication_config'
  patch_request.cluster = messages.Cluster(
      crossClusterReplicationConfig=new_ccr_config
  )
  return patch_request
