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

from googlecloudsdk.api_lib.container import api_adapter
from googlecloudsdk.api_lib.container import util
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.command_lib.container import constants
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import properties
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


def GetZone(args, ignore_property=False, required=True):
  """Get a zone from argument or property.

  Args:
    args: an argparse namespace. All the arguments that were provided to this
        command invocation.
    ignore_property: bool, if true, will get location only from argument.
    required: bool, if true, lack of zone will cause raise an exception.

  Raises:
    MinimumArgumentException: if location if required and not provided.

  Returns:
    str, a zone selected by user.
  """
  zone = getattr(args, 'zone', None)

  if ignore_property:
    zone_property = None
  else:
    zone_property = properties.VALUES.compute.zone.Get()

  if required and not zone and not zone_property:
    raise calliope_exceptions.MinimumArgumentException(
        ['--zone'], 'Please specify zone')

  return zone or zone_property


def GetZoneOrRegion(args, ignore_property=False, required=True):
  """Get a location (zone or region) from argument or property.

  Args:
    args: an argparse namespace. All the arguments that were provided to this
        command invocation.
    ignore_property: bool, if true, will get location only from argument.
    required: bool, if true, lack of zone will cause raise an exception.

  Raises:
    MinimumArgumentException: if location if required and not provided.
    ConflictingArgumentsException: if both --zone and --region arguments
        provided.

  Returns:
    str, a location selected by user.
  """
  zone = getattr(args, 'zone', None)
  region = getattr(args, 'region', None)

  if ignore_property:
    zone_property = None
  else:
    zone_property = properties.VALUES.compute.zone.Get()

  if zone and region:
    raise calliope_exceptions.ConflictingArgumentsException(
        '--zone', '--region')

  location = region or zone or zone_property
  if required and not location:
    raise calliope_exceptions.MinimumArgumentException(
        ['--zone', '--region'], 'Please specify location.')

  return location


def ParseUpdateOptionsBase(args, locations):
  """Helper function to build ClusterUpdateOptions object from args.

  Args:
    args: an argparse namespace. All the arguments that were provided to this
        command invocation.
    locations: list of strings. Zones in which cluster has nodes.

  Returns:
    ClusterUpdateOptions, object with data used to update cluster.
  """
  return api_adapter.UpdateClusterOptions(
      monitoring_service=args.monitoring_service,
      disable_addons=args.disable_addons,
      enable_autoscaling=args.enable_autoscaling,
      min_nodes=args.min_nodes,
      max_nodes=args.max_nodes,
      node_pool=args.node_pool,
      locations=locations,
      enable_master_authorized_networks=args.enable_master_authorized_networks,
      master_authorized_networks=args.master_authorized_networks)


def GetUseV1APIProperty():
  """Returns whether v1 API should be used."""

  new_set = properties.VALUES.container.use_v1_api.IsExplicitlySet()
  if new_set:
    new_val = properties.VALUES.container.use_v1_api.GetBool()

  old_set = properties.VALUES.container.use_v1_api_client.IsExplicitlySet()
  if old_set:
    old_val = properties.VALUES.container.use_v1_api_client.GetBool()

  # use_v1_api is set but use_v1_api_client is not set
  if new_set and not old_set:
    return new_val
  # use_v1_api is not set but use_v1_api_client is set
  elif not new_set and old_set:
    return old_val
  # both use_v1_api and use_v1_api_client are not set
  elif not new_set and not old_set:
    # default behavior is using v1 api
    return True
  # both use_v1_api and use_v1_api_client are set
  else:
    # if the values of use_v1_api and use_v1_api match, return either one
    if new_val == old_val:
      return new_val
    else:
      raise util.Error(
          constants.CANNOT_SET_BOTH_USE_V1_API_PROPERTIES_WITH_DIFF_VALUES)
