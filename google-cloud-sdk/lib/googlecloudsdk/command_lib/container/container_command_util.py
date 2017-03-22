# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Command util functions for gcloud container commands."""

from googlecloudsdk.core import exceptions
from googlecloudsdk.core.util import text


class Error(exceptions.Error):
  """Class for errors raised by container commands."""


class NodePoolError(Error):
  """Error when a node pool name doesn't match a node pool in the cluster."""


def _NodePoolFromCluster(cluster, node_pool_name):
  """Helper function to get node pool from a cluster, given its name."""
  for node_pool in cluster.nodePools:
    if node_pool.name == node_pool_name:
      # Node pools always have unique names.
      return node_pool
  raise NodePoolError('No node pool found matching the name [{}].'.format(
      node_pool_name))


def ClusterUpgradeMessage(cluster, master=False, node_pool=None,
                          new_version=None):
  """Get a message to print during gcloud container clusters upgrade.

  Args:
    cluster: the cluster object.
    master: bool, if the upgrade applies to the master version.
    node_pool: str, the name of the node pool if the upgrade is for a specific
        node pool.
    new_version: str, the name of the new version, if given.

  Raises:
    NodePoolError: if the node pool name can't be found in the cluster.

  Returns:
    str, a message about which nodes in the cluster will be upgraded and
        to which version.
  """
  if new_version:
    new_version_message = 'version [{}]'.format(new_version)
  else:
    new_version_message = 'master version'
  if master:
    node_message = 'Master'
    current_version = cluster.currentMasterVersion
  elif node_pool:
    node_message = 'All nodes in node pool [{}]'.format(node_pool)
    node_pool = _NodePoolFromCluster(cluster, node_pool)
    current_version = node_pool.version
  else:
    node_message = 'All nodes ({} {})'.format(
        cluster.currentNodeCount,
        text.Pluralize(cluster.currentNodeCount, 'node'))
    current_version = cluster.currentNodeVersion
  return ('{} of cluster [{}] will be upgraded from version [{}] to {}. '
          'This operation is long-running and will block other operations '
          'on the cluster (including delete) until it has run to completion.'
          .format(node_message, cluster.name, current_version,
                  new_version_message))
