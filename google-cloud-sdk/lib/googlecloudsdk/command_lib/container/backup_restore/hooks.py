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
"""Hooks for Backup for GKE command line arguments."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.container.backup_restore import util as api_util
from googlecloudsdk.calliope.exceptions import InvalidArgumentException
from googlecloudsdk.command_lib.export import util as export_util
from googlecloudsdk.core.console import console_io


def AddForceToDeleteRequest(ref, args, request):
  # Unused arguments.
  del ref
  del args

  # Add force=true to delete requests for backup and restore resources.
  request.force = True
  return request


def ParseClusterResourceRestoreScope(cluster_resource_restore_scope):
  """Process cluster-resource-restore-scope flag."""
  if not cluster_resource_restore_scope:
    return None
  message = api_util.GetMessagesModule()
  crrs = message.ClusterResourceRestoreScope()
  try:
    for resource in cluster_resource_restore_scope:
      group_kind = resource.split('/')
      if len(group_kind) == 1:
        group = ''
        kind = group_kind[0]
      elif len(group_kind) == 2:
        group, kind = group_kind
      else:
        raise InvalidArgumentException(
            '--cluster-resource-restore-scope',
            'Cluster resource restore scope is invalid.',
        )
      if not kind:
        raise InvalidArgumentException(
            '--cluster-resource-restore-scope',
            'Cluster resource restore scope kind is empty.')
      gk = message.GroupKind()
      gk.resourceGroup = group
      gk.resourceKind = kind
      crrs.selectedGroupKinds.append(gk)
    return crrs
  except ValueError:
    raise InvalidArgumentException(
        '--cluster-resource-restore-scope',
        'Cluster resource restore scope is invalid.')


def ProcessClusterResourceRestoreScope(cluster_resource_restore_scope):
  return ParseClusterResourceRestoreScope(cluster_resource_restore_scope)


def ProcessAllNamespaces(all_namespaces):
  if not all_namespaces:
    raise InvalidArgumentException('--all-namespaces',
                                   'All namespaces can only be true.')
  return all_namespaces


def ProcessSelectedNamespaces(selected_namespaces):
  if not selected_namespaces:
    raise InvalidArgumentException('--selected-namespaces',
                                   'Selected namespaces must not be empty.')
  return selected_namespaces


def ProcessSelectedApplications(selected_applications):
  """Processes selected-applications flag."""
  if not selected_applications:
    raise InvalidArgumentException('--selected-applications',
                                   'Selected applications must not be empty.')
  message = api_util.GetMessagesModule()
  sa = message.NamespacedNames()
  try:
    for namespaced_name in selected_applications.split(','):
      namespace, name = namespaced_name.split('/')
      if not namespace:
        raise InvalidArgumentException(
            '--selected-applications',
            'Namespace of selected application {0} is empty.'.format(
                namespaced_name))
      if not name:
        raise InvalidArgumentException(
            '--selected-applications',
            'Name of selected application {0} is empty.'.format(
                namespaced_name))
      nn = message.NamespacedName()
      nn.name = name
      nn.namespace = namespace
      sa.namespacedNames.append(nn)
    return sa
  except ValueError:
    raise InvalidArgumentException(
        '--selected-applications',
        'Selected applications {0} is invalid.'.format(selected_applications))


def PreprocessUpdateBackupPlan(ref, args, request):
  """Preprocesses request and update mask for backup update command."""
  del ref

  # Clear other fields in the backup scope mutex group.
  if args.IsSpecified('selected_namespaces'):
    request.backupPlan.backupConfig.selectedApplications = None
    request.backupPlan.backupConfig.allNamespaces = None
  if args.IsSpecified('selected_applications'):
    request.backupPlan.backupConfig.selectedNamespaces = None
    request.backupPlan.backupConfig.allNamespaces = None
  if args.IsSpecified('all_namespaces'):
    request.backupPlan.backupConfig.selectedApplications = None
    request.backupPlan.backupConfig.selectedNamespaces = None

  # Correct update mask for backup scope mutex group.
  new_masks = []
  for mask in request.updateMask.split(','):
    if mask.startswith('backupConfig.selectedNamespaces'):
      mask = 'backupConfig.selectedNamespaces'
    elif mask.startswith('backupConfig.selectedApplications'):
      mask = 'backupConfig.selectedApplications'
    # Other masks are unchanged.
    new_masks.append(mask)
  request.updateMask = ','.join(new_masks)
  return request


def GetSchemaPath():
  return export_util.GetSchemaPath('gkebackup', 'v1', 'SubstitutionRules')


def PreprocessUpdateRestorePlan(ref, args, request):
  """Preprocess request for updating restore plan."""
  del ref

  if args.IsSpecified('cluster_resource_restore_scope'):
    request.restorePlan.restoreConfig.clusterResourceRestoreScope = (
        ParseClusterResourceRestoreScope(args.cluster_resource_restore_scope)
    )

  # Guarded by argparser group with mutex=true.
  if args.IsSpecified('all_namespaces'):
    request.restorePlan.restoreConfig.selectedNamespaces = None
    request.restorePlan.restoreConfig.selectedApplications = None
  if args.IsSpecified('selected_namespaces'):
    request.restorePlan.restoreConfig.allNamespaces = None
    request.restorePlan.restoreConfig.selectedApplications = None
  if args.IsSpecified('selected_applications'):
    request.restorePlan.restoreConfig.allNamespaces = None
    request.restorePlan.restoreConfig.selectedNamespaces = None

  if args.IsSpecified('substitution_rules_file'):
    request.restorePlan.restoreConfig.substitutionRules = (
        ReadSubstitutionRuleFile(args.substitution_rules_file)
    )

  new_masks = []
  for mask in request.updateMask.split(','):
    if mask.startswith('restoreConfig.selectedNamespaces'):
      mask = 'restoreConfig.selectedNamespaces'
    elif mask.startswith('restoreConfig.selectedApplications'):
      mask = 'restoreConfig.selectedApplications'
    # Other masks are unchanged
    new_masks.append(mask)
  request.updateMask = ','.join(new_masks)
  return request


def ReadSubstitutionRuleFile(file_arg):
  """Reads content of the substitution rule file specified in file_arg."""
  if not file_arg:
    return None
  data = console_io.ReadFromFileOrStdin(file_arg, binary=False)
  messages = api_util.GetMessagesModule()
  temp_restore_config = export_util.Import(
      message_type=messages.RestoreConfig,
      stream=data,
      schema_path=GetSchemaPath())
  return temp_restore_config.substitutionRules
