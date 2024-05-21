# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Cloud Spanner backup schedules API helper."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.command_lib.spanner.resource_args import CloudKmsKeyName
from googlecloudsdk.core.util import times


def ParseAndFormatRetentionDuration(retention_duration):
  return times.FormatDurationForJson(times.ParseDuration(retention_duration))


def CreateBackupScheduleMessage(
    backup_schedule_ref,
    args,
    msgs,
    encryption_type=None,
    kms_key: CloudKmsKeyName = None,
):
  """Create a backup schedule message.

  Args:
    backup_schedule_ref: resource argument for a cloud spanner backup schedule.
    args: an argparse namespace. All the arguments that were provided to command
      invocation.
    msgs: contains the definitions of messages for the spanner v1 API.
    encryption_type: encryption type for the backup encryption.
    kms_key: contains the encryption keys for the backup encryption.

  Returns:
    BackupSchedule message.
  """
  backup_schedule = msgs.BackupSchedule(name=backup_schedule_ref.RelativeName())

  if args.retention_duration:
    backup_schedule.retentionDuration = ParseAndFormatRetentionDuration(
        args.retention_duration
    )

  if encryption_type or kms_key:
    encryption_config = msgs.CreateBackupEncryptionConfig()
    if encryption_type:
      encryption_config.encryptionType = encryption_type
    if kms_key:
      if kms_key.kms_key_name:
        encryption_config.kmsKeyName = kms_key.kms_key_name
      elif kms_key.kms_key_names:
        encryption_config.kmsKeyNames = kms_key.kms_key_names
    backup_schedule.encryptionConfig = encryption_config

  backup_schedule.fullBackupSpec = msgs.FullBackupSpec()

  if args.cron:
    backup_schedule.spec = msgs.BackupScheduleSpec(
        cronSpec=msgs.CrontabSpec(text=args.cron)
    )
  return backup_schedule


def Get(backup_schedule_ref):
  """Get a backup schedule."""
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')
  req = msgs.SpannerProjectsInstancesDatabasesBackupSchedulesGetRequest(
      name=backup_schedule_ref.RelativeName()
  )
  return client.projects_instances_databases_backupSchedules.Get(req)


def Delete(backup_schedule_ref):
  """Delete a backup schedule."""
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')
  req = msgs.SpannerProjectsInstancesDatabasesBackupSchedulesDeleteRequest(
      name=backup_schedule_ref.RelativeName()
  )
  return client.projects_instances_databases_backupSchedules.Delete(req)


def Create(
    backup_schedule_ref,
    args,
    encryption_type,
    kms_key,
):
  """Create a new backup schedule."""
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')
  req = msgs.SpannerProjectsInstancesDatabasesBackupSchedulesCreateRequest(
      parent=backup_schedule_ref.Parent().RelativeName()
  )
  req.backupSchedule = CreateBackupScheduleMessage(
      backup_schedule_ref, args, msgs, encryption_type, kms_key
  )
  req.backupScheduleId = backup_schedule_ref.Name()
  return client.projects_instances_databases_backupSchedules.Create(req)


def List(database_ref):
  """List backup schedules in the database."""
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')
  req = msgs.SpannerProjectsInstancesDatabasesBackupSchedulesListRequest(
      parent=database_ref.RelativeName()
  )
  return list_pager.YieldFromList(
      client.projects_instances_databases_backupSchedules,
      req,
      field='backupSchedules',
      batch_size_attribute='pageSize',
  )


def Update(
    backup_schedule_ref,
    args,
    encryption_type,
    kms_key,
):
  """Update a backup schedule."""
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')
  req = msgs.SpannerProjectsInstancesDatabasesBackupSchedulesPatchRequest(
      name=backup_schedule_ref.RelativeName()
  )
  req.backupSchedule = CreateBackupScheduleMessage(
      backup_schedule_ref, args, msgs, encryption_type, kms_key
  )

  update_mask_paths = []
  if args.cron:
    update_mask_paths.append('spec.cron_spec.text')
  if args.retention_duration:
    update_mask_paths.append('retention_duration')
  if encryption_type or kms_key:
    update_mask_paths.append('encryption_config')
  req.updateMask = ','.join(update_mask_paths)

  return client.projects_instances_databases_backupSchedules.Patch(req)
