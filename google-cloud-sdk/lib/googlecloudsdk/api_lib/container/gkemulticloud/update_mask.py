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

AZURE_CLUSTER_ARGS_TO_UPDATE_MASKS = {
    'client': 'azure_client',
    'cluster_version': 'control_plane.version',
    'vm_size': 'control_plane.vm_size',
    'admin_users': 'authorization.admin_users',
}

AZURE_NODEPOOL_ARGS_TO_UPDATE_MASKS = {
    'min_nodes': 'autoscaling.minNodeCount',
    'max_nodes': 'autoscaling.maxNodeCount',
    'node_version': 'version',
}


def GetUpdateMask(args, args_to_update_masks):
  update_mask_list = []
  for arg in args_to_update_masks:
    if hasattr(args, arg) and args.IsSpecified(arg):
      update_mask_list.append(args_to_update_masks[arg])
  return ','.join(sorted(set(update_mask_list)))
