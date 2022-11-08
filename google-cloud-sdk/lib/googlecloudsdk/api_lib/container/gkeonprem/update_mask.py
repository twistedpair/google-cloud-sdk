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
"""Utilities for working with update mask."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

VMWARE_CLUSTER_ARGS_TO_UPDATE_MASKS = {
    'description': 'description',
}

VMWARE_NODE_POOL_ARGS_TO_UPDATE_MASKS = {
    'display_name': 'display_name',
    'min_replicas': 'node_pool_autoscaling.min_replicas',
    'max_replicas': 'node_pool_autoscaling.max_replicas',
    'cpus': 'config.cpus',
    'memory': 'config.memory_mb',
    'replicas': 'config.replicas',
    'image_type': 'config.image_type',
    'image': 'config.image',
    'boot_disk_size': 'config.boot_disk_size_gb',
    'node_taints': 'config.taints',
    'node_labels': 'config.labels',
    'enable_load_balancer': 'config.enable_load_balancer',
    'disable_load_balancer': 'config.enable_load_balancer',
}

VMWARE_ADMIN_CLUSTER_ARGS_TO_UPDATE_MASKS = {
    'required_platform_version': 'platform_config.required_platform_version',
}

BARE_METAL_CLUSTER_ARGS_TO_UPDATE_MASKS = {
    'metal_lb_config_address_pools':
        'load_balancer.metal_lb_config.address_pools',
}

BARE_METAL_NODE_POOL_ARGS_TO_UPDATE_MASKS = {
    'node_configs': 'node_pool_config.node_configs',
}


def get_update_mask(args, args_to_update_masks):
  """Maps user provided arguments to API supported mutable fields in format of yaml field paths.

  Args:
    args: All arguments passed from CLI.
    args_to_update_masks: Mapping for a specific resource, such as user cluster,
      or node pool.

  Returns:
    A string that contains yaml field paths to be used in the API update
    request.
  """
  update_mask_list = []
  for arg in args_to_update_masks:
    if hasattr(args, arg) and args.IsSpecified(arg):
      update_mask_list.append(args_to_update_masks[arg])
  return ','.join(sorted(set(update_mask_list)))
