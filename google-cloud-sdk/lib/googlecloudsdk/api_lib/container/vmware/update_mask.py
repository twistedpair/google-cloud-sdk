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
    'replicas': 'config.replicas',
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
