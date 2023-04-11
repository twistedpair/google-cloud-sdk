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
from googlecloudsdk.core import properties


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


def _ConstructContinuousBackupConfig(alloydb_messages, args, update=False):
  """Returns the continuous backup config based on args."""
  continuous_backup_config = alloydb_messages.ContinuousBackupConfig()

  flags.ValidateContinuousBackupFlags(args, update)
  if args.enable_continuous_backup:
    continuous_backup_config.enabled = True
  elif args.enable_continuous_backup is False:  # pylint: disable=g-bool-id-comparison
    continuous_backup_config.enabled = False
    return continuous_backup_config

  if args.continuous_backup_recovery_window_days:
    continuous_backup_config.recoveryWindowDays = (
        args.continuous_backup_recovery_window_days
    )
  kms_key = flags.GetAndValidateKmsKeyName(
      args, flag_overrides=flags.GetContinuousBackupKmsFlagOverrides())

  if kms_key:
    encryption_config = alloydb_messages.EncryptionConfig()
    encryption_config.kmsKeyName = kms_key
    continuous_backup_config.encryptionConfig = encryption_config
  return continuous_backup_config


def _ConstructClusterForCreateRequestGA(alloydb_messages, args):
  """Returns the cluster for GA create request based on args."""
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

  return cluster


def _ConstructClusterForCreateRequestBeta(alloydb_messages, args):
  """Returns the cluster for beta create request based on args."""
  cluster = _ConstructClusterForCreateRequestGA(alloydb_messages, args)

  if (
      args.enable_continuous_backup is not None
      or args.continuous_backup_recovery_window_days
      or args.continuous_backup_encryption_key
  ):
    cluster.continuousBackupConfig = _ConstructContinuousBackupConfig(
        alloydb_messages, args)

  return cluster


def _ConstructClusterForCreateRequestAlpha(alloydb_messages, args):
  """Returns the cluster for alpha create request based on args."""
  cluster = _ConstructClusterForCreateRequestBeta(alloydb_messages, args)

  if args.allocated_ip_range_name:
    cluster.networkConfig = alloydb_messages.NetworkConfig(
        network=args.network, allocatedIpRange=args.allocated_ip_range_name
    )

  return cluster


def ConstructCreateRequestFromArgsGA(alloydb_messages, location_ref, args):
  """Returns the cluster create request for GA track based on args."""
  cluster = _ConstructClusterForCreateRequestGA(alloydb_messages, args)

  return alloydb_messages.AlloydbProjectsLocationsClustersCreateRequest(
      cluster=cluster,
      clusterId=args.cluster,
      parent=location_ref.RelativeName())


def ConstructCreateRequestFromArgsBeta(alloydb_messages, location_ref, args):
  """Returns the cluster create request for beta track based on args."""
  cluster = _ConstructClusterForCreateRequestBeta(alloydb_messages, args)

  return alloydb_messages.AlloydbProjectsLocationsClustersCreateRequest(
      cluster=cluster,
      clusterId=args.cluster,
      parent=location_ref.RelativeName())


def ConstructCreateRequestFromArgsAlpha(alloydb_messages, location_ref, args):
  """Returns the cluster create request for alpha track based on args."""
  cluster = _ConstructClusterForCreateRequestAlpha(alloydb_messages, args)

  return alloydb_messages.AlloydbProjectsLocationsClustersCreateRequest(
      cluster=cluster,
      clusterId=args.cluster,
      parent=location_ref.RelativeName(),
  )


def _ConstructBackupSourceForRestoreRequest(alloydb_messages, resource_parser,
                                            args):
  """Returns the backup source for restore request."""
  backup_ref = resource_parser.Create(
      'alloydb.projects.locations.backups',
      projectsId=properties.VALUES.core.project.GetOrFail,
      locationsId=args.region,
      backupsId=args.backup)
  backup_source = alloydb_messages.BackupSource(
      backupName=backup_ref.RelativeName())
  return backup_source


def _ConstructClusterResourceForRestoreRequest(alloydb_messages, args):
  """Returns the cluster resource for restore request."""
  cluster_resource = alloydb_messages.Cluster()
  cluster_resource.network = args.network
  kms_key = flags.GetAndValidateKmsKeyName(args)
  if kms_key:
    encryption_config = alloydb_messages.EncryptionConfig()
    encryption_config.kmsKeyName = kms_key
    cluster_resource.encryptionConfig = encryption_config
  return cluster_resource


def ConstructRestoreRequestFromArgsGA(alloydb_messages, location_ref,
                                      resource_parser, args):
  """Returns the cluster restore request for GA track based on args."""
  cluster_resource = _ConstructClusterResourceForRestoreRequest(
      alloydb_messages, args)

  backup_source = _ConstructBackupSourceForRestoreRequest(
      alloydb_messages, resource_parser, args)

  return alloydb_messages.AlloydbProjectsLocationsClustersRestoreRequest(
      parent=location_ref.RelativeName(),
      restoreClusterRequest=alloydb_messages.RestoreClusterRequest(
          backupSource=backup_source,
          clusterId=args.cluster,
          cluster=cluster_resource,
      ))


def ConstructRestoreRequestFromArgsAlphaBeta(alloydb_messages, location_ref,
                                             resource_parser, args):
  """Returns the cluster restore request for alpha and beta tracks based on args.
  """
  cluster_resource = _ConstructClusterResourceForRestoreRequest(
      alloydb_messages, args)

  backup_source, continuous_backup_source = None, None
  if args.backup:
    backup_source = _ConstructBackupSourceForRestoreRequest(
        alloydb_messages, resource_parser, args)
  else:
    cluster_ref = resource_parser.Create(
        'alloydb.projects.locations.clusters',
        projectsId=properties.VALUES.core.project.GetOrFail,
        locationsId=args.region,
        clustersId=args.source_cluster)
    continuous_backup_source = alloydb_messages.ContinuousBackupSource(
        cluster=cluster_ref.RelativeName(),
        pointInTime=args.point_in_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
    )

  return alloydb_messages.AlloydbProjectsLocationsClustersRestoreRequest(
      parent=location_ref.RelativeName(),
      restoreClusterRequest=alloydb_messages.RestoreClusterRequest(
          backupSource=backup_source,
          continuousBackupSource=continuous_backup_source,
          clusterId=args.cluster,
          cluster=cluster_resource,
      ))


def _ConstructClusterAndMaskForPatchRequestGA(alloydb_messages, args):
  cluster = alloydb_messages.Cluster()
  update_masks = []

  if (args.disable_automated_backup or args.automated_backup_days_of_week or
      args.clear_automated_backup):
    cluster.automatedBackupPolicy = _ConstructAutomatedBackupPolicy(
        alloydb_messages, args)
    update_masks.append('automated_backup_policy')
  return cluster, update_masks


def _ConstructClusterAndMaskForPatchRequestAlphaBeta(alloydb_messages, args):
  """Returns the cluster patch request for Alpha/Beta track based on args."""
  cluster, update_masks = _ConstructClusterAndMaskForPatchRequestGA(
      alloydb_messages, args)
  continuous_backup_update_masks = []

  if args.enable_continuous_backup:
    continuous_backup_update_masks.append('continuous_backup_config.enabled')
  elif args.enable_continuous_backup is False:  # pylint: disable=g-bool-id-comparison
    # We apply the continuous_backup_config mask to clear the entire
    # configuration when disabling continuous backups
    update_masks.append('continuous_backup_config')
    cluster.continuousBackupConfig = _ConstructContinuousBackupConfig(
        alloydb_messages, args, update=True)
    return cluster, update_masks

  if args.continuous_backup_recovery_window_days:
    continuous_backup_update_masks.append(
        'continuous_backup_config.recovery_window_days'
    )
  if (
      args.continuous_backup_encryption_key
      or args.clear_continuous_backup_encryption_key
  ):
    continuous_backup_update_masks.append(
        'continuous_backup_config.encryption_config'
    )

  update_masks.extend(continuous_backup_update_masks)
  if continuous_backup_update_masks:
    cluster.continuousBackupConfig = _ConstructContinuousBackupConfig(
        alloydb_messages, args, update=True)
  return cluster, update_masks


def ConstructPatchRequestFromArgsGA(alloydb_messages, cluster_ref, args):
  """Returns the cluster patch request for GA release track based on args."""
  cluster, update_masks = _ConstructClusterAndMaskForPatchRequestGA(
      alloydb_messages, args)
  return alloydb_messages.AlloydbProjectsLocationsClustersPatchRequest(
      name=cluster_ref.RelativeName(),
      cluster=cluster,
      updateMask=','.join(update_masks))


def ConstructPatchRequestFromArgsAlphaBeta(alloydb_messages, cluster_ref, args):
  """Returns the cluster patch request for alpha and beta release tracks based on args.
  """
  cluster, update_masks = _ConstructClusterAndMaskForPatchRequestAlphaBeta(
      alloydb_messages, args)
  return alloydb_messages.AlloydbProjectsLocationsClustersPatchRequest(
      name=cluster_ref.RelativeName(),
      cluster=cluster,
      updateMask=','.join(update_masks))
