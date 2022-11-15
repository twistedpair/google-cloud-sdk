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

ATTACHED_CLUSTER_ARGS_TO_UPDATE_MASKS = {
    'description': 'description',
    'annotations': 'annotations',
    'platform_version': 'platform_version',
    'admin_users': 'authorization.admin_users',
    'logging': 'logging_config.component_config.enable_components',
    'enable_managed_prometheus':
        'monitoring_config.managed_prometheus_config.enabled',
    'disable_managed_prometheus':
        'monitoring_config.managed_prometheus_config.enabled',
}

AWS_CLUSTER_ARGS_TO_UPDATE_MASKS = {
    'cluster_version':
        'control_plane.version',
    'instance_type':
        'control_plane.instance_type',
    'config_encryption_kms_key_arn':
        'control_plane.config_encryption.kms_key_arn',
    'clear_security_group_ids':
        'control_plane.security_group_ids',
    'security_group_ids':
        'control_plane.security_group_ids',
    'root_volume_size':
        'control_plane.root_volume.size_gib',
    'root_volume_type':
        'control_plane.root_volume.volume_type',
    'root_volume_iops':
        'control_plane.root_volume.iops',
    'root_volume_kms_key_arn':
        'control_plane.root_volume.kms_key_arn',
    'role_arn':
        'control_plane.aws_services_authentication.role_arn',
    'role_session_name':
        'control_plane.aws_services_authentication.role_session_name',
    'admin_users':
        'authorization.admin_users',
    'clear_proxy_config':
        'control_plane.proxy_config',
    'proxy_secret_arn':
        'control_plane.proxy_config.secret_arn',
    'proxy_secret_version_id':
        'control_plane.proxy_config.secret_version',
    'ssh_ec2_key_pair':
        'control_plane.ssh_config.ec2_key_pair',
    'clear_ssh_ec2_key_pair':
        'control_plane.ssh_config.ec2_key_pair',
    'iam_instance_profile':
        'control_plane.iam_instance_profile',
    'logging':
        'logging_config.component_config.enable_components',
    'enable_managed_prometheus':
        'monitoring_config.managed_prometheus_config.enabled',
    'disable_managed_prometheus':
        'monitoring_config.managed_prometheus_config.enabled',
    'description':
        'description',
    'clear_description':
        'description',
    'annotations':
        'annotations',
    'clear_annotations':
        'annotations',
    'tags':
        'control_plane.tags',
    'clear_tags':
        'control_plane.tags'
}

AWS_NODEPOOL_ARGS_TO_UPDATE_MASKS = {
    'node_version': 'version',
    'min_nodes': 'autoscaling.minNodeCount',
    'max_nodes': 'autoscaling.maxNodeCount',
    'clear_security_group_ids': 'config.security_group_ids',
    'security_group_ids': 'config.security_group_ids',
    'config_encryption_kms_key_arn': 'config.config_encryption.kms_key_arn',
    'root_volume_size': 'config.root_volume.size_gib',
    'root_volume_type': 'config.root_volume.volume_type',
    'root_volume_iops': 'config.root_volume.iops',
    'root_volume_kms_key_arn': 'config.root_volume.kms_key_arn',
    'clear_proxy_config': 'config.proxy_config',
    'proxy_secret_arn': 'config.proxy_config.secret_arn',
    'proxy_secret_version_id': 'config.proxy_config.secret_version',
    'ssh_ec2_key_pair': 'config.ssh_config.ec2_key_pair',
    'clear_ssh_ec2_key_pair': 'config.ssh_config.ec2_key_pair',
    'iam_instance_profile': 'config.iam_instance_profile',
    'annotations': 'annotations',
    'clear_annotations': 'annotations'
}

AZURE_CLUSTER_ARGS_TO_UPDATE_MASKS = {
    'client': 'azure_client',
    'cluster_version': 'control_plane.version',
    'vm_size': 'control_plane.vm_size',
    'admin_users': 'authorization.admin_users',
    'ssh_public_key': 'control_plane.ssh_config.authorized_key',
    'logging': 'logging_config.component_config.enable_components',
    'enable_managed_prometheus':
        'monitoring_config.managed_prometheus_config.enabled',
    'disable_managed_prometheus':
        'monitoring_config.managed_prometheus_config.enabled',
    'description': 'description',
    'clear_description': 'description',
    'annotations': 'annotations',
    'clear_annotations': 'annotations'
}

AZURE_NODEPOOL_ARGS_TO_UPDATE_MASKS = {
    'min_nodes': 'autoscaling.minNodeCount',
    'max_nodes': 'autoscaling.maxNodeCount',
    'node_version': 'version',
    'ssh_public_key': 'config.ssh_config.authorized_key',
    'annotations': 'annotations',
    'clear_annotations': 'annotations'
}


def GetUpdateMask(args, args_to_update_masks):
  update_mask_list = []
  for arg in args_to_update_masks:
    if hasattr(args, arg) and args.IsSpecified(arg):
      update_mask_list.append(args_to_update_masks[arg])
  return ','.join(sorted(set(update_mask_list)))
