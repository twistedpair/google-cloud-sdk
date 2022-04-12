# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Utilities for building the dataproc clusters gke CLI."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import exceptions


def AddPoolsArg(parser):
  parser.add_argument(
      '--pools',
      type=arg_parsers.ArgDict(
          required_keys=[
              'name',
              'roles',
          ],
          spec={
              'name': str,
              'roles': str,
              'machineType': str,
              'preemptible': arg_parsers.ArgBoolean(),
              'localSsdCount': int,
              'accelerators': str,
              'minCpuPlatform': str,
              'locations': str,
              'min': int,
              'max': int,
          },
      ),
      action='append',
      default=[],
      metavar='KEY=VALUE[;VALUE]',
      help="""
        Each `--pools` flag represents a single GKE node pool associated with
        the virtual cluster. It is comprised of a CSV in the form
        `KEY=VALUE[;VALUE]`, where certain keys may have multiple values.

        The following KEYs must be specified:

        KEY | Type | Example | Description
        --- |  --- | --- | ---
        name | string | `my-node-pool` | Name of the node pool.
        roles | repeated string | `default;spark-driver` | Roles that this node pool should perform. Valid values are `default`, `controller`, `spark-driver`, `spark-executor`.

        The following KEYs may be specified.

        KEY | Type | Example | Description
        --- | --- | --- | ---
        machineType | string | `n1-standard-8` | Compute Engine machine type to use.
        preemptible | boolean | `false` | If true, then this node pool uses preemptible VMs. This cannot be true on the node pool with the `controllers` role (or `default` role if `controllers` role is not specified).
        localSsdCount | int | `2` | The number of local SSDs to attach to each node.
        accelerator | repeated string | `nvidia-tesla-a100=1` | Accelerators to attach to each node. In the format NAME=COUNT.
        minCpuPlatform | string | `Intel Skylake` | Minimum CPU platform for each node.
        locations | repeated string | `us-west1-a;us-west1-c` | Zones within the location of the GKE cluster. All `--pools` flags for a single Dataproc cluster must have identical locations.
        min | int | `0` | Minimum number of nodes per zone that this node pool can scale down to.
        max | int | `10` | Maximum number of nodes per zone that this node pool can scale up to.
        """)


class GkeNodePoolTargetsParser():
  """Parses all the --pools flags into a list of GkeNodePoolTarget messages."""

  @staticmethod
  def Parse(dataproc, gke_cluster, arg_pools):
    """Parses all the --pools flags into a list of GkeNodePoolTarget messages.

    Args:
      dataproc: The Dataproc API version to use for GkeNodePoolTarget
        messages.
      gke_cluster: The GKE cluster's relative name, for example,
        'projects/p1/locations/l1/clusters/c1'.
      arg_pools: The list of dict[str, any] generated from all --pools flags.

    Returns:
      A list of GkeNodePoolTargets message, one for each entry in the arg_pools
      list.
    """
    pools = [
        _GkeNodePoolTargetParser.Parse(dataproc, gke_cluster, arg_pool)
        for arg_pool in arg_pools
    ]
    GkeNodePoolTargetsParser._ValidateUniqueNames(pools)
    GkeNodePoolTargetsParser._ValidateRoles(dataproc, pools)
    GkeNodePoolTargetsParser._ValidatePoolsHaveSameLocation(pools)
    return pools

  @staticmethod
  def _ValidateUniqueNames(pools):
    """Validates that pools have unique names."""
    used_names = set()
    for pool in pools:
      name = pool.nodePool
      if name in used_names:
        raise exceptions.InvalidArgumentException(
            '--pools', 'Pool name "%s" used more than once.' % name)
      used_names.add(name)

  @staticmethod
  def _ValidateRoles(dataproc, pools):
    """Validates that roles are exclusive and that one pool has DEFAULT."""
    if not pools:
      # The backend will automatically create the default pool.
      return
    seen_roles = set()
    for pool in pools:
      for role in pool.roles:
        if role in seen_roles:
          raise exceptions.InvalidArgumentException(
              '--pools', 'Multiple pools contained the same role "%s".' % role)
        else:
          seen_roles.add(role)

    default = dataproc.messages.GkeNodePoolTarget.RolesValueListEntryValuesEnum(
        'DEFAULT')
    if default not in seen_roles:
      raise exceptions.InvalidArgumentException(
          '--pools',
          'If any pools are specified, then exactly one must have the '
          '"default" role.')

  @staticmethod
  def _ValidatePoolsHaveSameLocation(pools):
    """Validates that all pools specify an identical location."""
    if not pools:
      return
    initial_locations = None
    for pool in pools:
      if pool.nodePoolConfig is not None:
        locations = pool.nodePoolConfig.locations
        if initial_locations is None:
          initial_locations = locations
          continue
        elif initial_locations != locations:
          raise exceptions.InvalidArgumentException(
              '--pools', 'All pools must have identical locations.')


class _GkeNodePoolTargetParser():
  """Helper to parse a single --pools flag into a GkeNodePoolTarget message."""

  _ARG_ROLE_TO_API_ROLE = {
      'default': 'DEFAULT',
      'controller': 'CONTROLLER',
      'spark-driver': 'SPARK_DRIVER',
      'spark-executor': 'SPARK_EXECUTOR',
  }

  @staticmethod
  def Parse(dataproc, gke_cluster, arg_pool):
    """Parses a single --pools flag into a GkeNodePoolTarget message.

    Args:
      dataproc: The Dataproc API version to use for the GkeNodePoolTarget
        message.
      gke_cluster: The GKE cluster's relative name, for example,
        'projects/p1/locations/l1/clusters/c1'.
      arg_pool: The dict[str, any] generated from the --pools flag.

    Returns:
      A GkeNodePoolTarget message.
    """
    return _GkeNodePoolTargetParser._GkeNodePoolTargetFromArgPool(
        dataproc, gke_cluster, arg_pool)

  @staticmethod
  def _GkeNodePoolTargetFromArgPool(dataproc, gke_cluster, arg_pool):
    """Creates a GkeNodePoolTarget from a single --pool argument."""
    return dataproc.messages.GkeNodePoolTarget(
        nodePool='{0}/nodePools/{1}'.format(gke_cluster, arg_pool['name']),
        roles=_GkeNodePoolTargetParser._SplitRoles(dataproc, arg_pool['roles']),
        nodePoolConfig=_GkeNodePoolTargetParser._GkeNodePoolConfigFromArgPool(
            dataproc, arg_pool))

  @staticmethod
  def _SplitRoles(dataproc, arg_roles):
    """Splits the role string given as an argument into a list of Role enums."""
    roles = []
    for arg_role in arg_roles.split(';'):
      if arg_role.lower() not in _GkeNodePoolTargetParser._ARG_ROLE_TO_API_ROLE:
        raise exceptions.InvalidArgumentException(
            '--pools', 'Unrecognized role "%s".' % arg_role)
      roles.append(
          dataproc.messages.GkeNodePoolTarget.RolesValueListEntryValuesEnum(
              _GkeNodePoolTargetParser._ARG_ROLE_TO_API_ROLE[arg_role.lower()]))
    return roles

  @staticmethod
  def _GkeNodePoolConfigFromArgPool(dataproc, arg_pool):
    """Creates the GkeNodePoolConfig via the arguments specified in --pools."""
    config = dataproc.messages.GkeNodePoolConfig(
        config=_GkeNodePoolTargetParser._GkeNodeConfigFromArgPool(
            dataproc, arg_pool),
        autoscaling=_GkeNodePoolTargetParser
        ._GkeNodePoolAutoscalingConfigFromArgPool(dataproc, arg_pool))
    if 'locations' in arg_pool:
      config.locations = arg_pool['locations'].split(';')
    if config != dataproc.messages.GkeNodePoolConfig():
      return config
    return None

  @staticmethod
  def _GkeNodeConfigFromArgPool(dataproc, arg_pool):
    """Creates the GkeNodeConfig via the arguments specified in --pools."""
    pool = dataproc.messages.GkeNodeConfig()
    if 'machineType' in arg_pool:
      pool.machineType = arg_pool['machineType']
    if 'preemptible' in arg_pool:
      # The ArgDict's spec declares this as an ArgBoolean(), so it is a boolean.
      pool.preemptible = arg_pool['preemptible']
    if 'localSsdCount' in arg_pool:
      # The ArgDict's spec declares this as an int, so it is an int.
      pool.localSsdCount = arg_pool['localSsdCount']
    if 'accelerators' in arg_pool:
      pool.accelerators = _GkeNodePoolTargetParser._GkeNodePoolAcceleratorConfigFromArgPool(
          dataproc, arg_pool['accelerators'])
    if 'minCpuPlatform' in arg_pool:
      pool.minCpuPlatform = arg_pool['minCpuPlatform']
    if pool != dataproc.messages.GkeNodeConfig():
      return pool
    return None

  @staticmethod
  def _GkeNodePoolAcceleratorConfigFromArgPool(dataproc, arg_accelerators):
    """Creates the GkeNodePoolAcceleratorConfig via the arguments specified in --pools."""
    accelerators = []
    for arg_accelerator in arg_accelerators.split(';'):
      if '=' not in arg_accelerator:
        raise exceptions.InvalidArgumentException(
            '--pools', 'accelerators value "%s" does not match the expected '
            '"ACCELERATOR_TYPE=ACCELERATOR_VALUE" pattern.' % arg_accelerator)

      accelerator_type, count_string = arg_accelerator.split('=', 1)
      try:
        count = int(count_string)
        accelerators.append(
            dataproc.messages.GkeNodePoolAcceleratorConfig(
                acceleratorCount=count,
                acceleratorType=accelerator_type,
            ))
      except ValueError:
        raise exceptions.InvalidArgumentException(
            '--pools',
            'Unable to parse accelerators count "%s" as an integer.' %
            count_string)
    return accelerators

  @staticmethod
  def _GkeNodePoolAutoscalingConfigFromArgPool(dataproc, arg_pool):
    """Creates the GkeNodePoolAutoscalingConfig via the arguments specified in --pools."""
    config = dataproc.messages.GkeNodePoolAutoscalingConfig()
    if 'min' in arg_pool:
      # The ArgDict's spec declares this as an int, so it is an int.
      config.minNodeCount = arg_pool['min']
    if 'max' in arg_pool:
      # The ArgDict's spec declares this as an int, so it is an int.
      config.maxNodeCount = arg_pool['max']
    if config != dataproc.messages.GkeNodePoolAutoscalingConfig():
      return config
    return None
