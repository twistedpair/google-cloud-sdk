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

from typing import Optional

from apitools.base.protorpclite import messages
from googlecloudsdk.api_lib.container.backup_restore import util as api_util
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.export import util as export_util
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io

CLUSTER_RESOURCE_SELECTED_GROUP_KINDS = 'cluster_resource_selected_group_kinds'
CLUSTER_RESOURCE_EXCLUDED_GROUP_KINDS = 'cluster_resource_excluded_group_kinds'
CLUSTER_RESOURCE_ALL_GROUP_KINDS = 'cluster_resource_all_group_kinds'
CLUSTER_RESOURCE_NO_GROUP_KINDS = 'cluster_resource_no_group_kinds'


def AddForceToDeleteRequest(ref, args, request):
  # Unused arguments.
  del ref
  del args

  # Add force=true to delete requests for backup and restore resources.
  request.force = True
  return request


def ParseGroupKinds(group_kinds, flag):
  """Process list of group kinds."""
  if not group_kinds:
    return None
  message = api_util.GetMessagesModule()
  gks = []
  try:
    for resource in group_kinds:
      group_kind = resource.split('/')
      if len(group_kind) == 1:
        group = ''
        kind = group_kind[0]
      elif len(group_kind) == 2:
        group, kind = group_kind
      else:
        raise exceptions.InvalidArgumentException(
            flag,
            'Cluster resource scope selected group kinds is invalid.',
        )
      if not kind:
        raise exceptions.InvalidArgumentException(
            flag,
            'Cluster resource scope selected group kinds is empty.')
      gk = message.GroupKind()
      gk.resourceGroup = group
      gk.resourceKind = kind
      gks.append(gk)
    return gks
  except ValueError:
    raise exceptions.InvalidArgumentException(
        flag,
        'Cluster resource scope selected group kinds is invalid.')


def ProcessSelectedGroupKinds(group_kinds):
  message = api_util.GetMessagesModule()
  crrs = message.ClusterResourceRestoreScope()
  crrs.selectedGroupKinds.extend(
      ParseGroupKinds(
          group_kinds, '--cluster-resource-scope-selected-group-kinds'
      )
  )
  return crrs


def ProcessExcludedGroupKinds(group_kinds):
  message = api_util.GetMessagesModule()
  crrs = message.ClusterResourceRestoreScope()
  crrs.excludedGroupKinds.extend(
      ParseGroupKinds(
          group_kinds, '--cluster-resource-scope-excluded-group-kinds'
      )
  )
  return crrs


def ProcessAllGroupKinds(all_group_kinds):
  message = api_util.GetMessagesModule()
  crrs = message.ClusterResourceRestoreScope()
  crrs.allGroupKinds = all_group_kinds
  return crrs


def ProcessNoGroupKinds(no_group_kinds):
  message = api_util.GetMessagesModule()
  crrs = message.ClusterResourceRestoreScope()
  crrs.noGroupKinds = no_group_kinds
  return crrs


def ProcessAllNamespaces(all_namespaces):
  if not all_namespaces:
    raise exceptions.InvalidArgumentException(
        '--all-namespaces',
        'All namespaces can only be true.')
  return all_namespaces


def ProcessNoNamespaces(no_namespaces):
  if not no_namespaces:
    raise exceptions.InvalidArgumentException(
        '--no-namespaces',
        'No namespaces can only be true.')
  return no_namespaces


def ProcessSelectedNamespaces(selected_namespaces):
  if not selected_namespaces:
    raise exceptions.InvalidArgumentException(
        '--selected-namespaces',
        'Selected namespaces must not be empty.')
  return selected_namespaces


def ProcessExcludedNamespaces(excluded_namespaces):
  if not excluded_namespaces:
    raise exceptions.InvalidArgumentException(
        '--excluded-namespaces',
        'Excluded namespaces must not be empty.')
  return excluded_namespaces


def ProcessSelectedApplications(selected_applications):
  """Processes selected-applications flag."""
  if not selected_applications:
    raise exceptions.InvalidArgumentException(
        '--selected-applications',
        'Selected applications must not be empty.')
  message = api_util.GetMessagesModule()
  sa = message.NamespacedNames()
  try:
    for namespaced_name in selected_applications.split(','):
      namespace, name = namespaced_name.split('/')
      if not namespace:
        raise exceptions.InvalidArgumentException(
            '--selected-applications',
            'Namespace of selected application {0} is empty.'.format(
                namespaced_name))
      if not name:
        raise exceptions.InvalidArgumentException(
            '--selected-applications',
            'Name of selected application {0} is empty.'.format(
                namespaced_name))
      nn = message.NamespacedName()
      nn.name = name
      nn.namespace = namespace
      sa.namespacedNames.append(nn)
    return sa
  except ValueError:
    raise exceptions.InvalidArgumentException(
        '--selected-applications',
        'Selected applications {0} is invalid.'.format(selected_applications),
    )


def ProcessSelectedNamespaceLabels(selected_namespace_labels):
  """Processes selected-namespace-labels flag."""
  if not selected_namespace_labels:
    raise exceptions.InvalidArgumentException(
        '--selected-namespace-labels',
        'Input for selected-namespace-labels must not be empty.',
    )
  message = api_util.GetMessagesModule()

  rls = message.ResourceLabels()
  for key_value_pair in selected_namespace_labels.split(','):
    parts = key_value_pair.split('=')
    if not parts[0]:
      raise exceptions.InvalidArgumentException(
          '--selected-namespace-labels',
          'Key of namespace label cannot be empty.',
      )
    rl = message.Label()
    rl.key = parts[0]
    rl.value = '' if len(parts) == 1 else parts[1]
    rls.resourceLabels.append(rl)
  return rls


def PreprocessUpdateBackupPlan(ref, args, request):
  """Preprocesses request and update mask for backup update command."""
  del ref

  # Clear other fields in the backup scope and backup schedule mutex group.
  if args.IsSpecified('selected_namespaces'):
    request.backupPlan.backupConfig.selectedApplications = None
    request.backupPlan.backupConfig.allNamespaces = None
  if args.IsSpecified('selected_applications'):
    request.backupPlan.backupConfig.selectedNamespaces = None
    request.backupPlan.backupConfig.allNamespaces = None
  if args.IsSpecified('all_namespaces'):
    request.backupPlan.backupConfig.selectedApplications = None
    request.backupPlan.backupConfig.selectedNamespaces = None

  # Unlike creation, update with both flags can result in both fields cleared
  # using the below logic, so we need to catch and error out here early.
  if (args.IsSpecified('target_rpo_minutes') and
      args.IsSpecified('cron_schedule')):
    raise exceptions.InvalidArgumentException(
        '--cron-schedule',
        'Cannot specify both --target_rpo_minutes and --cron_schedule.')

  if args.IsSpecified('target_rpo_minutes'):
    request.backupPlan.backupSchedule.cronSchedule = None
  if args.IsSpecified('cron_schedule'):
    request.backupPlan.backupSchedule.rpoConfig = None

  # Correct update mask for backup scope and backup schedule mutex group.
  new_masks = set()
  for mask in request.updateMask.split(','):
    if mask.startswith('backupConfig.selectedNamespaces'):
      new_masks.add('backupConfig.selectedNamespaces')
    elif mask.startswith('backupConfig.selectedApplications'):
      new_masks.add('backupConfig.selectedApplications')
    elif mask.startswith('backupSchedule.cronSchedule'):
      new_masks.add('backupSchedule.cronSchedule')
      new_masks.add('backupSchedule.rpoConfig')
    elif mask.startswith('backupSchedule.rpoConfig.targetRpoMinutes'):
      new_masks.add('backupSchedule.rpoConfig.targetRpoMinutes')
      new_masks.add('backupSchedule.cronSchedule')
    else:
      new_masks.add(mask)
  # use set to dedup and canonicalize
  request.updateMask = ','.join(sorted(new_masks))
  return request


def PreprocessUpdateRestorePlan(ref, args, request):
  """Preprocess request for updating restore plan."""
  del ref

  # Guarded by argparser group with mutex=true.
  if hasattr(
      args, CLUSTER_RESOURCE_SELECTED_GROUP_KINDS
  ) and args.IsSpecified(CLUSTER_RESOURCE_SELECTED_GROUP_KINDS):
    request.restorePlan.restoreConfig.clusterResourceRestoreScope = (
        ProcessSelectedGroupKinds(args.cluster_resource_selected_group_kinds)
    )
  if hasattr(
      args, CLUSTER_RESOURCE_EXCLUDED_GROUP_KINDS
  ) and args.IsSpecified(CLUSTER_RESOURCE_EXCLUDED_GROUP_KINDS):
    request.restorePlan.restoreConfig.clusterResourceRestoreScope = (
        ProcessExcludedGroupKinds(args.cluster_resource_excluded_group_kinds)
    )
  if hasattr(args, CLUSTER_RESOURCE_ALL_GROUP_KINDS) and args.IsSpecified(
      CLUSTER_RESOURCE_ALL_GROUP_KINDS
  ):
    request.restorePlan.restoreConfig.clusterResourceRestoreScope = (
        ProcessAllGroupKinds(args.cluster_resource_all_group_kinds)
    )
  if hasattr(args, CLUSTER_RESOURCE_NO_GROUP_KINDS) and args.IsSpecified(
      CLUSTER_RESOURCE_NO_GROUP_KINDS
  ):
    request.restorePlan.restoreConfig.clusterResourceRestoreScope = (
        ProcessNoGroupKinds(args.cluster_resource_no_group_kinds)
    )

  # Guarded by argparser group with mutex=true.
  if args.IsSpecified('all_namespaces'):
    request.restorePlan.restoreConfig.noNamespaces = None
    request.restorePlan.restoreConfig.selectedNamespaces = None
    request.restorePlan.restoreConfig.excludedNamespaces = None
    request.restorePlan.restoreConfig.selectedApplications = None
  if args.IsSpecified('no_namespaces'):
    request.restorePlan.restoreConfig.allNamespaces = None
    request.restorePlan.restoreConfig.selectedNamespaces = None
    request.restorePlan.restoreConfig.excludedNamespaces = None
    request.restorePlan.restoreConfig.selectedApplications = None
  if args.IsSpecified('selected_namespaces'):
    request.restorePlan.restoreConfig.allNamespaces = None
    request.restorePlan.restoreConfig.noNamespaces = None
    request.restorePlan.restoreConfig.excludedNamespaces = None
    request.restorePlan.restoreConfig.selectedApplications = None
  if args.IsSpecified('excluded_namespaces'):
    request.restorePlan.restoreConfig.allNamespaces = None
    request.restorePlan.restoreConfig.noNamespaces = None
    request.restorePlan.restoreConfig.selectedNamespaces = None
    request.restorePlan.restoreConfig.selectedApplications = None
  if args.IsSpecified('selected_applications'):
    request.restorePlan.restoreConfig.allNamespaces = None
    request.restorePlan.restoreConfig.noNamespaces = None
    request.restorePlan.restoreConfig.selectedNamespaces = None
    request.restorePlan.restoreConfig.excludedNamespaces = None

  new_masks = []

  if (
      args.IsSpecified('substitution_rules_file')
      and bool(request.restorePlan.restoreConfig.transformationRules)
  ):
    console_io.PromptContinue(
        """
      The given restore plan already has the transformation rules. Updating the
      restore plan with new substitution rules will delete the existing
      transformation rules.
      """,
        cancel_on_no=True,
    )
    # Set transformationRules to be empty, and add it into update masks.
    request.restorePlan.restoreConfig.transformationRules = messages.FieldList(
        messages.StringField(number=1, repeated=True), []
    )
    new_masks.append('restoreConfig.transformationRules')

  if (
      args.IsSpecified('transformation_rules_file')
      and bool(request.restorePlan.restoreConfig.substitutionRules)
  ):
    console_io.PromptContinue(
        """
      The given restore plan already has the substitution rules. Updating the
      restore plan with new transformation rules will delete the existing
      substitution rules.
      """,
        cancel_on_no=True,
    )
    # Set substitutionRules to be empty, and add it into update masks.
    request.restorePlan.restoreConfig.substitutionRules = messages.FieldList(
        messages.StringField(number=1, repeated=True), []
    )
    new_masks.append('restoreConfig.substitutionRules')

  for mask in request.updateMask.split(','):
    if mask.startswith('restoreConfig.selectedNamespaces'):
      mask = 'restoreConfig.selectedNamespaces'
    elif mask.startswith('restoreConfig.excludedNamespaces'):
      mask = 'restoreConfig.excludedNamespaces'
    elif mask.startswith('restoreConfig.selectedApplications'):
      mask = 'restoreConfig.selectedApplications'
    elif mask.startswith('restoreConfig.noNamespaces'):
      mask = 'restoreConfig.noNamespaces'
    elif mask.startswith('restoreConfig.allNamespaces'):
      mask = 'restoreConfig.allNamespaces'
    # Other masks are unchanged
    new_masks.append(mask)
  request.updateMask = ','.join(new_masks)
  return request


def ReadSubstitutionRuleFile(file_arg):
  """Reads content of the substitution rule file specified in file_arg."""
  if not file_arg:
    return messages.FieldList(messages.StringField(number=1, repeated=True), [])
  log.warning(
      'The substitutionRules field is deprecated and can only be managed via'
      ' gcloud/API. Please migrate to transformation rules.'
  )
  data = console_io.ReadFromFileOrStdin(file_arg, binary=False)
  ms = api_util.GetMessagesModule()
  temp_restore_config = export_util.Import(
      message_type=ms.RestoreConfig,
      stream=data,
      schema_path=export_util.GetSchemaPath(
          'gkebackup', 'v1', 'SubstitutionRules'
      ),
  )
  return temp_restore_config.substitutionRules


def ReadTransformationRuleFile(file_arg):
  """Reads content of the transformation rule file specified in file_arg."""
  if not file_arg:
    return None
  data = console_io.ReadFromFileOrStdin(file_arg, binary=False)
  ms = api_util.GetMessagesModule()
  temp_restore_config = export_util.Import(
      message_type=ms.RestoreConfig,
      stream=data,
      schema_path=export_util.GetSchemaPath(
          'gkebackup', 'v1', 'TransformationRules'
      ),
  )
  return temp_restore_config.transformationRules


def ReadRestoreOrderFile(file_arg):
  """Reads content of the restore order file specified in file_arg."""
  if not file_arg:
    return None
  data = console_io.ReadFromFileOrStdin(file_arg, binary=False)
  ms = api_util.GetMessagesModule()
  temp_restore_order = export_util.Import(
      message_type=ms.RestoreOrder,
      stream=data,
      schema_path=export_util.GetSchemaPath(
          'gkebackup', 'v1', 'RestoreOrder'
      ),
  )
  return temp_restore_order


def ReadExclusionWindowsFile(file_arg):
  """Reads content of the exclusion window file specified in file_arg."""
  if not file_arg:
    return None
  data = console_io.ReadFromFileOrStdin(file_arg, binary=False)
  ms = api_util.GetMessagesModule()
  temp_rpo_config = export_util.Import(
      message_type=ms.RpoConfig,
      stream=data,
      schema_path=export_util.GetSchemaPath(
          'gkebackup', 'v1', 'ExclusionWindows'
      ),
  )
  return temp_rpo_config.exclusionWindows


def ReadVolumeDataRestorePolicyOverridesFile(
    file_arg: Optional[str]
) -> Optional[api_util.VolumeDataRestorePolicyOverrides]:
  """Reads the volume data restore policy overrides file."""
  if not file_arg:
    return None
  data = console_io.ReadFromFileOrStdin(file_arg, binary=False)
  ms = api_util.GetMessagesModule()
  return export_util.Import(
      message_type=ms.Restore,
      stream=data,
      schema_path=export_util.GetSchemaPath(
          'gkebackup', 'v1', 'VolumeDataRestorePolicyOverrides'
      ),
  ).volumeDataRestorePolicyOverrides


def ReadRestoreFilterFile(file_arg):
  """Reads content of the restore filter file specified in file_arg."""
  if not file_arg:
    return None
  data = console_io.ReadFromFileOrStdin(file_arg, binary=False)
  try:
    restore_filter = export_util.Import(
        message_type=api_util.GetMessagesModule().Filter,
        stream=data,
        schema_path=export_util.GetSchemaPath(
            'gkebackup', 'v1', 'Filter'
        ),
    )
  except Exception as e:
    raise exceptions.InvalidArgumentException(
        '--filter-file',
        '{0}'.format(e))

  return restore_filter
