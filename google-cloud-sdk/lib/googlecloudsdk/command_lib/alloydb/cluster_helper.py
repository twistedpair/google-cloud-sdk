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
"""Helper functions for constructing and validating AlloyDB cluster requests."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.alloydb import flags


def _ConstructAutomatedBackupPolicy(alloydb_messages, args):
  """Returns the automated backup policy based on args."""
  backup_policy = alloydb_messages.AutomatedBackupPolicy()
  if args.disable_automated_backup:
    backup_policy.enabled = False
  elif args.automated_backup_days_of_week:
    backup_policy.enabled = True
    backup_policy.weeklySchedule = alloydb_messages.WeeklySchedule(
        daysOfWeek=args.automated_backup_days_of_week,
        startTimes=args.automated_backup_start_times,
    )
    if args.automated_backup_retention_count:
      backup_policy.quantityBasedRetention = (
          alloydb_messages.QuantityBasedRetention(
              count=args.automated_backup_retention_count))
    elif args.automated_backup_retention_period:
      backup_policy.timeBasedRetention = (
          alloydb_messages.TimeBasedRetention(retentionPeriod='{}s'.format(
              args.automated_backup_retention_period)))
    if args.automated_backup_window:
      backup_policy.backupWindow = '{}s'.format(args.automated_backup_window)
    kms_key = flags.GetAndValidateKmsKeyName(
        args, flag_overrides=flags.GetAutomatedBackupKmsFlagOverrides())
    if kms_key:
      encryption_config = alloydb_messages.EncryptionConfig()
      encryption_config.kmsKeyName = kms_key
      backup_policy.encryptionConfig = encryption_config
    backup_policy.location = args.region
  return backup_policy


def _ConstructPitrConfig(alloydb_messages, args):
  """Returns the pitr config based on args."""
  pitr_config = alloydb_messages.PitrConfig()
  if args.disable_pitr:
    pitr_config.enabled = False
  elif args.pitr_log_retention_window:
    pitr_config.enabled = True
    pitr_config.logRetentionWindow = '{}s'.format(
        args.pitr_log_retention_window)
  return pitr_config


def ConstructCreateRequestFromArgs(alloydb_messages, location_ref, args):
  """Returns the cluster create request based on args."""
  cluster = alloydb_messages.Cluster()
  cluster.network = args.network
  cluster.initialUser = alloydb_messages.UserPassword(
      password=args.password, user='postgres')
  kms_key = flags.GetAndValidateKmsKeyName(args)
  if kms_key:
    encryption_config = alloydb_messages.EncryptionConfig()
    encryption_config.kmsKeyName = kms_key
    cluster.encryptionConfig = encryption_config

  if args.disable_automated_backup or args.automated_backup_days_of_week:
    cluster.automatedBackupPolicy = _ConstructAutomatedBackupPolicy(
        alloydb_messages, args)

  if args.disable_pitr or args.pitr_log_retention_window:
    cluster.pitrConfig = _ConstructPitrConfig(alloydb_messages, args)

  return alloydb_messages.AlloydbProjectsLocationsClustersCreateRequest(
      cluster=cluster,
      clusterId=args.cluster,
      parent=location_ref.RelativeName())


def ConstructPatchRequestFromArgs(alloydb_messages, cluster_ref, args):
  """Returns the cluster patch request based on args."""
  update_masks = []
  cluster = alloydb_messages.Cluster()

  if (args.disable_automated_backup or args.automated_backup_days_of_week or
      args.clear_automated_backup):
    cluster.automatedBackupPolicy = _ConstructAutomatedBackupPolicy(
        alloydb_messages, args)
    update_masks.append('automated_backup_policy')

  if args.disable_pitr or args.pitr_log_retention_window:
    cluster.pitrConfig = _ConstructPitrConfig(alloydb_messages, args)
    update_masks.append('pitr_config')

  return alloydb_messages.AlloydbProjectsLocationsClustersPatchRequest(
      name=cluster_ref.RelativeName(),
      cluster=cluster,
      updateMask=','.join(update_masks))
