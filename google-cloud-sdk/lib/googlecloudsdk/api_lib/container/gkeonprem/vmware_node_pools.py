# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Utilities for node pool resources in Anthos clusters on VMware."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.container.gkeonprem import client
from googlecloudsdk.api_lib.container.gkeonprem import update_mask
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.container.vmware import flags

import six


class NodePoolsClient(client.ClientBase):
  """Client for node pools in Anthos clusters on VMware API."""

  def __init__(self, **kwargs):
    super(NodePoolsClient, self).__init__(**kwargs)
    self._service = self._client.projects_locations_vmwareClusters_vmwareNodePools

  def List(self, args):
    """Lists Node Pools in the Anthos clusters on VMware API."""
    list_req = self._messages.GkeonpremProjectsLocationsVmwareClustersVmwareNodePoolsListRequest(
        parent=self._user_cluster_name(args))
    return list_pager.YieldFromList(
        self._service,
        list_req,
        field='vmwareNodePools',
        batch_size=flags.Get(args, 'page_size'),
        limit=flags.Get(args, 'limit'),
        batch_size_attribute='pageSize',
    )

  def Delete(self, args):
    """Deletes a gkeonprem node pool API resource."""
    kwargs = {
        'allowMissing': flags.Get(args, 'allow_missing'),
        'etag': flags.Get(args, 'etag'),
        'name': self._node_pool_name(args),
        'validateOnly': flags.Get(args, 'validate_only'),
        'ignoreErrors': flags.Get(args, 'ignore_errors'),
    }
    req = self._messages.GkeonpremProjectsLocationsVmwareClustersVmwareNodePoolsDeleteRequest(
        **kwargs)
    return self._service.Delete(req)

  def Create(self, args):
    """Creates a gkeonprem node pool API resource."""
    node_pool_ref = self._node_pool_ref(args)
    kwargs = {
        'parent': node_pool_ref.Parent().RelativeName(),
        'validateOnly': flags.Get(args, 'validate_only'),
        'vmwareNodePool': self._vmware_node_pool(args),
        'vmwareNodePoolId': self._node_pool_id(args),
    }
    req = self._messages.GkeonpremProjectsLocationsVmwareClustersVmwareNodePoolsCreateRequest(
        **kwargs)
    return self._service.Create(req)

  def Update(self, args):
    """Updates a gkeonprem node pool API resource."""
    kwargs = {
        'allowMissing':
            flags.Get(args, 'allow_missing'),
        'name':
            self._node_pool_name(args),
        'updateMask':
            update_mask.get_update_mask(
                args, update_mask.VMWARE_NODE_POOL_ARGS_TO_UPDATE_MASKS),
        'validateOnly':
            flags.Get(args, 'validate_only'),
        'vmwareNodePool':
            self._vmware_node_pool(args),
    }
    req = self._messages.GkeonpremProjectsLocationsVmwareClustersVmwareNodePoolsPatchRequest(
        **kwargs)
    return self._service.Patch(req)

  def _vmware_node_pool(self, args):
    """Constructs proto message VmwareNodePool."""
    kwargs = {
        'name': self._node_pool_name(args),
        'displayName': flags.Get(args, 'display_name'),
        'annotations': self._annotations(args),
        'config': self._vmware_node_config(args),
        'nodePoolAutoscaling': self._vmware_node_pool_autoscaling_config(args),
    }
    return self._messages.VmwareNodePool(**kwargs)

  def _enable_load_balancer(self, args):
    if flags.Get(args, 'enable_load_balancer'):
      return True
    if flags.Get(args, 'disable_load_balancer'):
      return False
    return None

  def _parse_node_taint(self, node_taint):
    """Validates and parses a node taint object.

    Args:
      node_taint: tuple, of format (TAINT_KEY, value), where value is a string
        of format TAINT_VALUE=EFFECT.

    Returns:
      If taint is valid, returns a dict mapping message NodeTaint to its value;
      otherwise, raise ArgumentTypeError.
      For example,
      {
          'key': TAINT_KEY
          'value': TAINT_VALUE
          'effect': EFFECT
      }
    """
    taint_effect_enum = self._messages.NodeTaint.EffectValueValuesEnum
    taint_effect_mapping = {
        'NoSchedule': taint_effect_enum.NO_SCHEDULE,
        'PreferNoSchedule': taint_effect_enum.PREFER_NO_SCHEDULE,
        'NoExecute': taint_effect_enum.NO_EXECUTE,
    }

    input_node_taint = '='.join(node_taint)
    valid_node_taint_effects = ', '.join(
        six.text_type(key) for key in sorted(taint_effect_mapping.keys()))

    if len(node_taint) != 2:
      raise arg_parsers.ArgumentTypeError(
          'Node taint [{}] not in correct format, expect KEY=VALUE:EFFECT.'
          .format(input_node_taint))
    taint_key = node_taint[0]

    effect_delimiter_count = node_taint[1].count(':')
    if effect_delimiter_count > 1:
      raise arg_parsers.ArgumentTypeError(
          'Node taint [{}] not in correct format, expect KEY=VALUE:EFFECT.'
          .format(input_node_taint))

    if effect_delimiter_count == 0:
      taint_value = node_taint[1]
      raise arg_parsers.ArgumentTypeError(
          'Taint effect unspecified: [{}], expect one of [{}].'.format(
              input_node_taint, valid_node_taint_effects))

    if effect_delimiter_count == 1:
      taint_value, taint_effect = node_taint[1].split(':', 1)
      if taint_effect not in taint_effect_mapping:
        raise arg_parsers.ArgumentTypeError(
            'Invalid taint effect in [{}] , expect one of [{}]'.format(
                input_node_taint, valid_node_taint_effects))

      taint_effect = taint_effect_mapping[taint_effect]

    ret = {'key': taint_key, 'value': taint_value, 'effect': taint_effect}
    return ret

  def _node_taints(self, args):
    taint_messages = []
    node_taints = flags.Get(args, 'node_taints', {})
    for node_taint in node_taints.items():
      taint_object = self._parse_node_taint(node_taint)
      taint_messages.append(self._messages.NodeTaint(**taint_object))
    return taint_messages

  def _labels_value(self, args):
    """Constructs proto message LabelsValue."""
    node_labels = flags.Get(args, 'node_labels', {})
    additional_property_messages = []
    if not node_labels:
      return None

    for key, value in node_labels.items():
      additional_property_messages.append(
          self._messages.VmwareNodeConfig.LabelsValue.AdditionalProperty(
              key=key, value=value))

    labels_value_message = self._messages.VmwareNodeConfig.LabelsValue(
        additionalProperties=additional_property_messages)

    return labels_value_message

  def _vmware_node_config(self, args):
    """Constructs proto message VmwareNodeConfig."""
    kwargs = {
        'cpus': flags.Get(args, 'cpus'),
        'memoryMb': flags.Get(args, 'memory'),
        'replicas': flags.Get(args, 'replicas'),
        'imageType': flags.Get(args, 'image_type'),
        'image': flags.Get(args, 'image'),
        'bootDiskSizeGb': flags.Get(args, 'boot_disk_size'),
        'taints': self._node_taints(args),
        'labels': self._labels_value(args),
        'enableLoadBalancer': self._enable_load_balancer(args),
    }
    if flags.IsSet(kwargs):
      return self._messages.VmwareNodeConfig(**kwargs)
    return None

  def _vmware_node_pool_autoscaling_config(self, args):
    """Constructs proto message VmwareNodePoolAutoscalingConfig."""
    kwargs = {
        'minReplicas': flags.Get(args, 'min_replicas'),
        'maxReplicas': flags.Get(args, 'max_replicas'),
    }
    if any(kwargs.values()):
      return self._messages.VmwareNodePoolAutoscalingConfig(**kwargs)
    return None

  def _annotations(self, args):
    """Constructs proto message AnnotationsValue."""
    annotations = flags.Get(args, 'annotations', {})
    additional_property_messages = []
    if not annotations:
      return None

    for key, value in annotations.items():
      additional_property_messages.append(
          self._messages.VmwareNodePool.AnnotationsValue.AdditionalProperty(
              key=key, value=value))

    annotation_value_message = self._messages.VmwareNodePool.AnnotationsValue(
        additionalProperties=additional_property_messages)
    return annotation_value_message
