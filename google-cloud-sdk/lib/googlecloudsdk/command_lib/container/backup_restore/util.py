# -*- coding: utf-8 -*- #
# Copyright 2021 Google Inc. All Rights Reserved.
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
"""Command line utilities for Backup for GKE commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.container.backup_restore import util as api_util
from googlecloudsdk.calliope.exceptions import BadArgumentException
from googlecloudsdk.command_lib.export import util as export_util
from googlecloudsdk.core.console import console_io


def GetSchemaPath():
  return export_util.GetSchemaPath('gkebackup', 'v1alpha1', 'SubstitutionRules')


def GetRestoreConfig(args):
  """Returns a restore config from command line arguments."""
  messages = api_util.GetMessagesModule()
  restore_config = messages.RestoreConfig()

  # Guarded by argparse
  if args.cluster_resource_conflict_policy == 'USE_EXISTING_VERSION':
    restore_config.clusterResourceConflictPolicy = messages.RestoreConfig.ClusterResourceConflictPolicyValueValuesEnum.USE_EXISTING_VERSION
  elif args.cluster_resource_conflict_policy == 'USE_BACKUP_VERSION':
    restore_config.clusterResourceConflictPolicy = messages.RestoreConfig.ClusterResourceConflictPolicyValueValuesEnum.USE_BACKUP_VERSION

  # Guarded by argparse
  if args.namespaced_resource_restore_mode == 'DELETE_AND_RESTORE':
    restore_config.namespacedResourceRestoreMode = messages.RestoreConfig.NamespacedResourceRestoreModeValueValuesEnum.DELETE_AND_RESTORE
  elif args.namespaced_resource_restore_mode == 'FAIL_ON_CONFLICT':
    restore_config.namespacedResourceRestoreMode = messages.RestoreConfig.NamespacedResourceRestoreModeValueValuesEnum.FAIL_ON_CONFLICT

  if args.IsSpecified('volume_data_restore_policy'):
    if args.volume_data_restore_policy == 'RESTORE_VOLUME_DATA_FROM_BACKUP':
      restore_config.volumeDataRestorePolicy = messages.RestoreConfig.VolumeDataRestorePolicyValueValuesEnum.RESTORE_VOLUME_DATA_FROM_BACKUP
    elif args.volume_data_restore_policy == 'REUSE_VOLUME_HANDLE_FROM_BACKUP':
      restore_config.volumeDataRestorePolicy = messages.RestoreConfig.VolumeDataRestorePolicyValueValuesEnum.REUSE_VOLUME_HANDLE_FROM_BACKUP
  else:
    restore_config.volumeDataRestorePolicy = messages.RestoreConfig.VolumeDataRestorePolicyValueValuesEnum.NO_VOLUME_DATA_RESTORATION

  cluster_resource_restore_scope = messages.ClusterResourceRestoreScope()
  if args.IsSpecified('cluster_resource_restore_scope'):
    for cr in args.cluster_resource_restore_scope.split(','):
      group_kind = cr.split('/')
      # Regular group kind in the format of <group>/<kind>
      if len(group_kind) == 2:
        gk = messages.GroupKind()
        gk.resourceGroup = group_kind[0]
        gk.resourceKind = group_kind[1]
        cluster_resource_restore_scope.selectedGroupKinds.append(gk)
      # We treat this case as user wanted to input kind from core group.
      elif len(group_kind) == 1:
        gk = messages.GroupKind()
        gk.resourceKind = group_kind[0]
        cluster_resource_restore_scope.selectedGroupKinds.append(gk)
      else:
        raise BadArgumentException(
            'cluster_resource_restore_scope',
            'Invalid cluster resource restore scope {0}.'.format(
                args.cluster_resource_restore_scope))
    restore_config.clusterResourceRestoreScope = cluster_resource_restore_scope

  # Guarded by argparser group with mutex=true.
  if args.IsSpecified('all_namespaces'):
    restore_config.allNamespaces = True
  if args.IsSpecified('selected_namespaces'):
    restore_config.selectedNamespaces = messages.Namespaces()
    for namespace in args.selected_namespaces.split(','):
      restore_config.selectedNamespaces.namespaces.append(namespace)
  if args.IsSpecified('selected_applications'):
    restore_config.selectedNamespaces = messages.NamespacedNames()
    for namespaced_name in args.selected_applications.split(','):
      elems = namespaced_name.split('/')
      if len(namespaced_name) != 2:
        raise BadArgumentException(
            'selected_applications',
            'Invalid selected applications {0}.'.format(
                args.selected_applications))
      nn = messages.NamespacedName()
      nn.name = elems[1]
      nn.namespace = elems[0]
      restore_config.selectedNamespaces.namespacedNames.append(nn)

  if args.IsSpecified('substitution_rules_file'):
    data = console_io.ReadFromFileOrStdin(
        args.substitution_rules_file, binary=False)
    messages = api_util.GetMessagesModule()
    temp_restore_config = export_util.Import(
        message_type=messages.RestoreConfig,
        stream=data,
        schema_path=GetSchemaPath())
    restore_config.substitutionRules = temp_restore_config.substitutionRules

  return restore_config
