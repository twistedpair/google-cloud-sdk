# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""Utils for VMware Engine private-clouds clusters commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
from typing import Any, Dict, List, Union

from googlecloudsdk.core import exceptions


class InvalidNodeConfigsProvidedError(exceptions.Error):

  def __init__(self, details):
    super(InvalidNodeConfigsProvidedError, self).__init__(
        f'INVALID_ARGUMENT: {details}'
    )


class InvalidAutoscalingSettingsProvidedError(exceptions.Error):

  def __init__(self, details):
    super(InvalidAutoscalingSettingsProvidedError, self).__init__(
        f'INVALID_ARGUMENT: {details}'
    )


NodeTypeConfig = collections.namedtuple(
    typename='NodeTypeConfig',
    field_names=['type', 'count', 'custom_core_count'],
)


def FindDuplicatedTypes(types):
  type_counts = collections.Counter(types)
  return [node_type for node_type, count in type_counts.items() if count > 1]


def ParseNodesConfigsParameters(nodes_configs):
  requested_node_types = [config['type'] for config in nodes_configs]

  duplicated_types = FindDuplicatedTypes(requested_node_types)
  if duplicated_types:
    raise InvalidNodeConfigsProvidedError(
        'types: {} provided more than once.'.format(duplicated_types)
    )

  return [
      NodeTypeConfig(
          config['type'], config['count'], config.get('custom-core-count', 0)
      )
      for config in nodes_configs
  ]


def ParseInlinedAutoscalingSettings(
    min_cluster_node_count: int,
    max_cluster_node_count: int,
    cool_down_period: str,
    autoscaling_policies: List[Dict[str, Union[str, int]]],
) -> Dict[str, Any]:
  """Parses inlined autoscaling settings (passed as CLI arguments) into a dict.

  The resulting dict can later be passed to
  googlecloudsdk.api_lib.vmware.util.ConstructAutoscalingSettingsMessage.

  Args:
    min_cluster_node_count: autoscaling-min-cluster-node-count CLI argument.
    max_cluster_node_count: autoscaling-max-cluster-node-count CLI argument.
    cool_down_period: autoscaling-cool-down-period CLI argument.
    autoscaling_policies: list of update-autoscaling-policy CLI arguments.

  Returns:
    Dict with the same structure as the output from the "describe" CLI
    command.
  """
  parsed_settings = {
      'minClusterNodeCount': min_cluster_node_count,
      'maxClusterNodeCount': max_cluster_node_count,
      'coolDownPeriod': cool_down_period,
      'autoscalingPolicies': {},
  }

  for policy in autoscaling_policies:
    parsed_policy = {
        'cpuThresholds': {},
        'grantedMemoryThresholds': {},
        'consumedMemoryThresholds': {},
        'storageThresholds': {},
    }

    parsed_policy['nodeTypeId'] = policy.get('node-type-id')
    parsed_policy['scaleOutSize'] = policy.get('scale-out-size')
    parsed_policy['minNodeCount'] = policy.get('min-node-count')
    parsed_policy['maxNodeCount'] = policy.get('max-node-count')
    parsed_policy['cpuThresholds']['scaleIn'] = policy.get(
        'cpu-thresholds-scale-in'
    )
    parsed_policy['cpuThresholds']['scaleOut'] = policy.get(
        'cpu-thresholds-scale-out'
    )
    parsed_policy['grantedMemoryThresholds']['scaleIn'] = policy.get(
        'granted-memory-thresholds-scale-in'
    )
    parsed_policy['grantedMemoryThresholds']['scaleOut'] = policy.get(
        'granted-memory-thresholds-scale-out'
    )
    parsed_policy['consumedMemoryThresholds']['scaleIn'] = policy.get(
        'consumed-memory-thresholds-scale-in'
    )
    parsed_policy['consumedMemoryThresholds']['scaleOut'] = policy.get(
        'consumed-memory-thresholds-scale-out'
    )
    parsed_policy['storageThresholds']['scaleIn'] = policy.get(
        'storage-thresholds-scale-in'
    )
    parsed_policy['storageThresholds']['scaleOut'] = policy.get(
        'storage-thresholds-scale-out'
    )

    parsed_settings['autoscalingPolicies'][policy['name']] = parsed_policy

  return parsed_settings
