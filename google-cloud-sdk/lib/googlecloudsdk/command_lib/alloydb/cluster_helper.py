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

import argparse
import types

from apitools.base.protorpclite import messages
from googlecloudsdk.command_lib.alloydb import flags
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


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
              count=args.automated_backup_retention_count
          )
      )
    elif args.automated_backup_retention_period:
      backup_policy.timeBasedRetention = alloydb_messages.TimeBasedRetention(
          retentionPeriod='{}s'.format(args.automated_backup_retention_period)
      )
    if args.automated_backup_window:
      backup_policy.backupWindow = '{}s'.format(args.automated_backup_window)
    kms_key = flags.GetAndValidateKmsKeyName(
        args, flag_overrides=flags.GetAutomatedBackupKmsFlagOverrides()
    )
    if kms_key:
      encryption_config = alloydb_messages.EncryptionConfig()
      encryption_config.kmsKeyName = kms_key
      backup_policy.encryptionConfig = encryption_config
    backup_policy.location = args.region
  return backup_policy


def _ConstructAutomatedBackupPolicyForCreateSecondary(alloydb_messages, args):
  """Returns the automated backup policy based on args."""
  automated_backup_policy = alloydb_messages.AutomatedBackupPolicy()
  if args.enable_automated_backup:
    automated_backup_policy.enabled = True
  elif args.enable_automated_backup is False:  # pylint: disable=g-bool-id-comparison
    automated_backup_policy.enabled = False
    return automated_backup_policy

  if args.automated_backup_window:
    automated_backup_policy.backupWindow = '{}s'.format(
        args.automated_backup_window
    )

  if args.automated_backup_days_of_week and args.automated_backup_start_times:
    automated_backup_policy.weeklySchedule = alloydb_messages.WeeklySchedule(
        daysOfWeek=args.automated_backup_days_of_week,
        startTimes=args.automated_backup_start_times,
    )

  if args.automated_backup_retention_count:
    automated_backup_policy.quantityBasedRetention = (
        alloydb_messages.QuantityBasedRetention(
            count=args.automated_backup_retention_count
        )
    )
  elif args.automated_backup_retention_period:
    automated_backup_policy.timeBasedRetention = (
        alloydb_messages.TimeBasedRetention(
            retentionPeriod='{}s'.format(args.automated_backup_retention_period)
        )
    )

  kms_key = flags.GetAndValidateKmsKeyName(
      args, flag_overrides=flags.GetAutomatedBackupKmsFlagOverrides()
  )
  if kms_key:
    encryption_config = alloydb_messages.EncryptionConfig()
    encryption_config.kmsKeyName = kms_key
    automated_backup_policy.encryptionConfig = encryption_config

  automated_backup_policy.location = args.region

  return automated_backup_policy


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
      args, flag_overrides=flags.GetContinuousBackupKmsFlagOverrides()
  )

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
      password=args.password, user='postgres'
  )
  kms_key = flags.GetAndValidateKmsKeyName(args)
  if kms_key:
    encryption_config = alloydb_messages.EncryptionConfig()
    encryption_config.kmsKeyName = kms_key
    cluster.encryptionConfig = encryption_config

  if args.disable_automated_backup or args.automated_backup_days_of_week:
    cluster.automatedBackupPolicy = _ConstructAutomatedBackupPolicy(
        alloydb_messages, args
    )

  if (
      args.enable_continuous_backup is not None
      or args.continuous_backup_recovery_window_days
      or args.continuous_backup_encryption_key
  ):
    cluster.continuousBackupConfig = _ConstructContinuousBackupConfig(
        alloydb_messages, args
    )

  if args.allocated_ip_range_name:
    cluster.networkConfig = alloydb_messages.NetworkConfig(
        network=args.network, allocatedIpRange=args.allocated_ip_range_name
    )

  if args.enable_private_service_connect:
    cluster.pscConfig = alloydb_messages.PscConfig(pscEnabled=True)

  cluster.databaseVersion = args.database_version

  configure_maintenance_window = (
      args.maintenance_window_day or args.maintenance_window_hour
  )
  configure_deny_period = (
      args.deny_maintenance_period_start_date
      or args.deny_maintenance_period_end_date
      or args.deny_maintenance_period_time
  )
  if configure_maintenance_window or configure_deny_period:
    cluster.maintenanceUpdatePolicy = alloydb_messages.MaintenanceUpdatePolicy()
  if configure_maintenance_window:
    cluster.maintenanceUpdatePolicy.maintenanceWindows = (
        _ConstructMaintenanceWindows(alloydb_messages, args)
    )
  if configure_deny_period:
    cluster.maintenanceUpdatePolicy.denyMaintenancePeriods = (
        _ConstructDenyPeriods(alloydb_messages, args)
    )

  cluster.subscriptionType = args.subscription_type
  cluster.tags = flags.GetTagsFromArgs(args, alloydb_messages.Cluster.TagsValue)
  return cluster


def _AddEnforcedRetentionToAutomatedBackupPolicy(backup_policy, args):
  if args.automated_backup_enforced_retention is not None:
    backup_policy.enforcedRetention = args.automated_backup_enforced_retention
  return backup_policy


def _AddEnforcedRetentionToContinuousBackupConfig(
    continuous_backup_config, args
):
  if args.continuous_backup_enforced_retention is not None:
    continuous_backup_config.enforcedRetention = (
        args.continuous_backup_enforced_retention
    )
  return continuous_backup_config


def _ConstructClusterForCreateRequestBeta(alloydb_messages, args):
  """Returns the cluster for beta create request based on args."""
  cluster = _ConstructClusterForCreateRequestGA(alloydb_messages, args)
  cluster.automatedBackupPolicy = _AddEnforcedRetentionToAutomatedBackupPolicy(
      cluster.automatedBackupPolicy, args
  )
  cluster.continuousBackupConfig = (
      _AddEnforcedRetentionToContinuousBackupConfig(
          cluster.continuousBackupConfig, args
      )
  )

  return cluster


def _ConstructClusterForCreateRequestAlpha(alloydb_messages, args):
  """Returns the cluster for alpha create request based on args."""
  flags.ValidateConnectivityFlags(args)
  cluster = _ConstructClusterForCreateRequestBeta(alloydb_messages, args)
  return cluster


def ConstructCreateRequestFromArgsGA(alloydb_messages, location_ref, args):
  """Returns the cluster create request for GA track based on args."""
  cluster = _ConstructClusterForCreateRequestGA(alloydb_messages, args)

  return alloydb_messages.AlloydbProjectsLocationsClustersCreateRequest(
      cluster=cluster,
      clusterId=args.cluster,
      parent=location_ref.RelativeName(),
  )


def ConstructCreateRequestFromArgsBeta(alloydb_messages, location_ref, args):
  """Returns the cluster create request for beta track based on args."""
  cluster = _ConstructClusterForCreateRequestBeta(alloydb_messages, args)

  return alloydb_messages.AlloydbProjectsLocationsClustersCreateRequest(
      cluster=cluster,
      clusterId=args.cluster,
      parent=location_ref.RelativeName(),
  )


def ConstructCreateRequestFromArgsAlpha(alloydb_messages, location_ref, args):
  """Returns the cluster create request for alpha track based on args."""
  cluster = _ConstructClusterForCreateRequestAlpha(alloydb_messages, args)

  return alloydb_messages.AlloydbProjectsLocationsClustersCreateRequest(
      cluster=cluster,
      clusterId=args.cluster,
      parent=location_ref.RelativeName(),
  )


def _ConstructBackupAndContinuousBackupSourceForRestoreRequest(
    alloydb_messages,
    resource_parser,
    args,
):
  """Returns the backup and continuous backup source for restore request."""
  # AlloyDB backup.
  if args.backup:
    backup_ref = resource_parser.Parse(
        collection='alloydb.projects.locations.backups',
        line=args.backup,
        params={
            'projectsId': properties.VALUES.core.project.GetOrFail,
            'locationsId': args.region,
        },
    )
    backup_source = alloydb_messages.BackupSource(
        backupName=backup_ref.RelativeName()
    )
    return backup_source, None, None

  # BackupDR backup.
  if hasattr(args, 'backupdr_backup') and args.backupdr_backup:
    backup_dr_backup_source = alloydb_messages.BackupDrBackupSource(
        backup=args.backupdr_backup,
    )
    return None, backup_dr_backup_source, None

  # AlloyDB source cluster is the remaining case.
  # Note the gcloud flags library guarantees that args.source_cluster is
  # specified.
  cluster_ref = resource_parser.Parse(
      collection='alloydb.projects.locations.clusters',
      line=args.source_cluster,
      params={
          'projectsId': properties.VALUES.core.project.GetOrFail,
          'locationsId': args.region,
      },
  )
  continuous_backup_source = alloydb_messages.ContinuousBackupSource(
      cluster=cluster_ref.RelativeName(),
      pointInTime=args.point_in_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
  )
  return None, None, continuous_backup_source


def _ConstructClusterResourceForRestoreRequest(alloydb_messages, args):
  """Returns the cluster resource for restore request."""
  cluster_resource = alloydb_messages.Cluster()
  cluster_resource.network = args.network
  kms_key = flags.GetAndValidateKmsKeyName(args)
  if kms_key:
    encryption_config = alloydb_messages.EncryptionConfig()
    encryption_config.kmsKeyName = kms_key
    cluster_resource.encryptionConfig = encryption_config

  if args.allocated_ip_range_name:
    cluster_resource.networkConfig = alloydb_messages.NetworkConfig(
        allocatedIpRange=args.allocated_ip_range_name
    )

  if args.enable_private_service_connect:
    cluster_resource.pscConfig = alloydb_messages.PscConfig(pscEnabled=True)

  if args.tags:
    cluster_resource.tags = flags.GetTagsFromArgs(
        args, alloydb_messages.Cluster.TagsValue
    )

  return cluster_resource


def ConstructRestoreRequestFromArgsGA(
    alloydb_messages, location_ref, resource_parser, args
):
  """Returns the cluster restore request for GA track based on args."""
  cluster_resource = _ConstructClusterResourceForRestoreRequest(
      alloydb_messages, args
  )

  backup_source, _, continuous_backup_source = (
      _ConstructBackupAndContinuousBackupSourceForRestoreRequest(
          alloydb_messages,
          resource_parser,
          args,
      )
  )

  return alloydb_messages.AlloydbProjectsLocationsClustersRestoreRequest(
      parent=location_ref.RelativeName(),
      restoreClusterRequest=alloydb_messages.RestoreClusterRequest(
          backupSource=backup_source,
          continuousBackupSource=continuous_backup_source,
          # TODO(b/400420101): support backup_dr_backup_source
          clusterId=args.cluster,
          cluster=cluster_resource,
      ),
  )


def _ConstructClusterResourceForRestoreRequestAlpha(alloydb_messages, args):
  """Returns the cluster resource for restore request."""
  cluster_resource = _ConstructClusterResourceForRestoreRequest(
      alloydb_messages, args
  )

  return cluster_resource


def ConstructRestoreRequestFromArgsAlpha(
    alloydb_messages, location_ref, resource_parser, args
):
  """Returns the cluster restore request for Alpha track based on args."""
  cluster_resource = _ConstructClusterResourceForRestoreRequestAlpha(
      alloydb_messages, args
  )

  backup_source, backup_dr_backup_source, continuous_backup_source = (
      _ConstructBackupAndContinuousBackupSourceForRestoreRequest(
          alloydb_messages,
          resource_parser,
          args,
      )
  )
  cluster_resource.tags = flags.GetTagsFromArgs(
      args, alloydb_messages.Cluster.TagsValue
  )
  return alloydb_messages.AlloydbProjectsLocationsClustersRestoreRequest(
      parent=location_ref.RelativeName(),
      restoreClusterRequest=alloydb_messages.RestoreClusterRequest(
          backupSource=backup_source,
          continuousBackupSource=continuous_backup_source,
          backupdrBackupSource=backup_dr_backup_source,
          clusterId=args.cluster,
          cluster=cluster_resource,
      ),
  )


def _ConstructClusterResourceForRestoreRequestBeta(alloydb_messages, args):
  """Returns the cluster resource for restore request."""
  cluster_resource = _ConstructClusterResourceForRestoreRequest(
      alloydb_messages, args
  )

  return cluster_resource


def ConstructRestoreRequestFromArgsBeta(
    alloydb_messages, location_ref, resource_parser, args
):
  """Returns the cluster restore request for Beta track based on args."""
  cluster_resource = _ConstructClusterResourceForRestoreRequestBeta(
      alloydb_messages, args
  )

  backup_source, backup_dr_backup_source, continuous_backup_source = (
      _ConstructBackupAndContinuousBackupSourceForRestoreRequest(
          alloydb_messages,
          resource_parser,
          args,
      )
  )

  return alloydb_messages.AlloydbProjectsLocationsClustersRestoreRequest(
      parent=location_ref.RelativeName(),
      restoreClusterRequest=alloydb_messages.RestoreClusterRequest(
          backupSource=backup_source,
          continuousBackupSource=continuous_backup_source,
          backupdrBackupSource=backup_dr_backup_source,
          clusterId=args.cluster,
          cluster=cluster_resource,
      ),
  )


def _ConstructClusterAndMaskForPatchRequestGA(alloydb_messages, args):
  """Returns the cluster resource for patch request."""
  cluster = alloydb_messages.Cluster()
  update_masks = []
  continuous_backup_update_masks = []

  if (
      args.disable_automated_backup
      or args.automated_backup_days_of_week
      or args.clear_automated_backup
  ):
    cluster.automatedBackupPolicy = _ConstructAutomatedBackupPolicy(
        alloydb_messages, args
    )
    update_masks.append('automated_backup_policy')

  if args.enable_continuous_backup:
    continuous_backup_update_masks.append('continuous_backup_config.enabled')
  elif args.enable_continuous_backup is False:  # pylint: disable=g-bool-id-comparison
    # We apply the continuous_backup_config mask to clear the entire
    # configuration when disabling continuous backups
    update_masks.append('continuous_backup_config')
    cluster.continuousBackupConfig = _ConstructContinuousBackupConfig(
        alloydb_messages, args, update=True
    )
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
        alloydb_messages, args, update=True
    )

  update_maintenance_window = (
      args.maintenance_window_any
      or args.maintenance_window_day
      or args.maintenance_window_hour
  )
  update_deny_period = (
      args.remove_deny_maintenance_period
      or args.deny_maintenance_period_start_date
      or args.deny_maintenance_period_end_date
      or args.deny_maintenance_period_time
  )
  if update_maintenance_window or update_deny_period:
    cluster.maintenanceUpdatePolicy = alloydb_messages.MaintenanceUpdatePolicy()
  if update_maintenance_window:
    cluster.maintenanceUpdatePolicy.maintenanceWindows = (
        _ConstructMaintenanceWindows(alloydb_messages, args, update=True)
    )
    update_masks.append('maintenance_update_policy.maintenance_windows')
  if update_deny_period:
    cluster.maintenanceUpdatePolicy.denyMaintenancePeriods = (
        _ConstructDenyPeriods(alloydb_messages, args, update=True)
    )
    update_masks.append('maintenance_update_policy.deny_maintenance_periods')

  if args.subscription_type is not None:
    cluster.subscriptionType = args.subscription_type
    update_masks.append('subscription_type')

  return cluster, update_masks


def _ConstructClusterAndMaskForPatchRequestBeta(alloydb_messages, args):
  """Returns the cluster resource for patch request."""
  cluster, update_masks = _ConstructClusterAndMaskForPatchRequestGA(
      alloydb_messages, args
  )
  if args.automated_backup_enforced_retention is not None:
    if cluster.automatedBackupPolicy is None:
      cluster.automatedBackupPolicy = _ConstructAutomatedBackupPolicy(
          alloydb_messages, args
      )
    update_masks.append('automated_backup_policy.enforced_retention')
    cluster.automatedBackupPolicy = (
        _AddEnforcedRetentionToAutomatedBackupPolicy(
            cluster.automatedBackupPolicy, args
        )
    )
  if args.continuous_backup_enforced_retention is not None:
    if cluster.continuousBackupConfig is None:
      cluster.continuousBackupConfig = _ConstructContinuousBackupConfig(
          alloydb_messages, args
      )
    update_masks.append('continuous_backup_config.enforced_retention')
    cluster.continuousBackupConfig = (
        _AddEnforcedRetentionToContinuousBackupConfig(
            cluster.continuousBackupConfig, args
        )
    )

  return cluster, update_masks


def _ConstructClusterAndMaskForPatchRequestAlpha(alloydb_messages, args):
  """Returns the cluster resource for patch request."""
  cluster, update_masks = _ConstructClusterAndMaskForPatchRequestBeta(
      alloydb_messages, args
  )
  return cluster, update_masks


def _ConstructMaintenanceWindows(alloydb_messages, args, update=False):
  """Returns the maintenance windows based on args."""
  if update and args.maintenance_window_any:
    return []

  maintenance_window = alloydb_messages.MaintenanceWindow()
  maintenance_window.day = args.maintenance_window_day
  maintenance_window.startTime = alloydb_messages.GoogleTypeTimeOfDay(
      hours=args.maintenance_window_hour
  )
  return [maintenance_window]


def _ConstructDenyPeriods(alloydb_messages, args, update=False):
  """Returns the deny periods based on args."""
  if update and args.remove_deny_maintenance_period:
    return []

  deny_period = alloydb_messages.DenyMaintenancePeriod()
  deny_period.startDate = args.deny_maintenance_period_start_date
  deny_period.endDate = args.deny_maintenance_period_end_date
  deny_period.time = args.deny_maintenance_period_time
  return [deny_period]


def ConstructPatchRequestFromArgsGA(alloydb_messages, cluster_ref, args):
  """Returns the cluster patch request for GA release track based on args."""
  cluster, update_masks = _ConstructClusterAndMaskForPatchRequestGA(
      alloydb_messages, args
  )
  return alloydb_messages.AlloydbProjectsLocationsClustersPatchRequest(
      name=cluster_ref.RelativeName(),
      cluster=cluster,
      updateMask=','.join(update_masks),
  )


def ConstructPatchRequestFromArgsBeta(alloydb_messages, cluster_ref, args):
  """Returns the cluster patch request for Beta release track based on args."""
  cluster, update_masks = _ConstructClusterAndMaskForPatchRequestBeta(
      alloydb_messages, args
  )
  return alloydb_messages.AlloydbProjectsLocationsClustersPatchRequest(
      name=cluster_ref.RelativeName(),
      cluster=cluster,
      updateMask=','.join(update_masks),
  )


def ConstructUpgradeRequestFromArgs(alloydb_messages, cluster_ref, args):
  """Returns the cluster upgrade request for Alpha release track based on args."""
  upgrade_cluster_request = alloydb_messages.UpgradeClusterRequest()
  upgrade_cluster_request.version = args.version
  return alloydb_messages.AlloydbProjectsLocationsClustersUpgradeRequest(
      name=cluster_ref.RelativeName(),
      upgradeClusterRequest=upgrade_cluster_request,
  )


def _ConstructClusterForCreateSecondaryRequestGA(alloydb_messages, args):
  """Returns the cluster for GA create-secondary request based on args."""
  cluster = alloydb_messages.Cluster()
  cluster.secondaryConfig = alloydb_messages.SecondaryConfig(
      primaryClusterName=args.primary_cluster
  )
  kms_key = flags.GetAndValidateKmsKeyName(args)
  if kms_key:
    encryption_config = alloydb_messages.EncryptionConfig()
    encryption_config.kmsKeyName = kms_key
    cluster.encryptionConfig = encryption_config

  if (
      args.enable_continuous_backup is not None
      or args.continuous_backup_recovery_window_days
      or args.continuous_backup_encryption_key
  ):
    cluster.continuousBackupConfig = _ConstructContinuousBackupConfig(
        alloydb_messages, args
    )

  if (
      args.enable_automated_backup is not None
      or args.automated_backup_days_of_week
      or args.automated_backup_window
      or args.automated_backup_start_times
  ):
    cluster.automatedBackupPolicy = (
        _ConstructAutomatedBackupPolicyForCreateSecondary(
            alloydb_messages, args
        )
    )

  if args.allocated_ip_range_name:
    cluster.networkConfig = alloydb_messages.NetworkConfig(
        allocatedIpRange=args.allocated_ip_range_name
    )

  if args.tags:
    cluster.tags = flags.GetTagsFromArgs(
        args, alloydb_messages.Cluster.TagsValue
    )
  return cluster


def _ConstructClusterForCreateSecondaryRequestBeta(alloydb_messages, args):
  cluster = _ConstructClusterForCreateSecondaryRequestGA(alloydb_messages, args)

  return cluster


def _ConstructClusterForCreateSecondaryRequestAlpha(alloydb_messages, args):
  cluster = _ConstructClusterForCreateSecondaryRequestBeta(
      alloydb_messages, args
  )
  return cluster


def ConstructCreatesecondaryRequestFromArgsGA(
    alloydb_messages, cluster_ref, args
):
  """Returns the cluster create-secondary request For GA release track based on args."""
  cluster = _ConstructClusterForCreateSecondaryRequestGA(alloydb_messages, args)
  return (
      alloydb_messages.AlloydbProjectsLocationsClustersCreatesecondaryRequest(
          cluster=cluster,
          clusterId=args.cluster,
          parent=cluster_ref.RelativeName(),
      )
  )


def ConstructCreatesecondaryRequestFromArgsBeta(
    alloydb_messages, cluster_ref, args
):
  """Returns the cluster create-secondary request for Beta release track based on args."""

  cluster = _ConstructClusterForCreateSecondaryRequestBeta(
      alloydb_messages, args
  )

  return (
      alloydb_messages.AlloydbProjectsLocationsClustersCreatesecondaryRequest(
          cluster=cluster,
          clusterId=args.cluster,
          parent=cluster_ref.RelativeName(),
      )
  )


def ConstructCreatesecondaryRequestFromArgsAlpha(
    alloydb_messages, cluster_ref, args
):
  """Returns the cluster create-secondary request for Alpha release track based on args."""

  cluster = _ConstructClusterForCreateSecondaryRequestAlpha(
      alloydb_messages, args
  )

  return (
      alloydb_messages.AlloydbProjectsLocationsClustersCreatesecondaryRequest(
          cluster=cluster,
          clusterId=args.cluster,
          parent=cluster_ref.RelativeName(),
      )
  )


def ConstructExportRequestFromArgs(alloydb_messages, cluster_ref, args):
  """Returns the cluster export request based on args."""
  export_cluster_request = alloydb_messages.ExportClusterRequest()
  export_cluster_request.database = args.database
  if args.csv:
    export_cluster_request.csvExportOptions = (
        alloydb_messages.CsvExportOptions()
    )
    export_cluster_request.csvExportOptions.selectQuery = args.select_query
    export_cluster_request.csvExportOptions.fieldDelimiter = (
        args.field_delimiter
    )
    export_cluster_request.csvExportOptions.escapeCharacter = (
        args.escape_character
    )
    export_cluster_request.csvExportOptions.quoteCharacter = (
        args.quote_character
    )
  elif args.sql:
    export_cluster_request.sqlExportOptions = (
        alloydb_messages.SqlExportOptions()
    )
    export_cluster_request.sqlExportOptions.schemaOnly = args.schema_only
    if args.tables:
      export_cluster_request.sqlExportOptions.tables = args.tables.split(',')
    export_cluster_request.sqlExportOptions.cleanTargetObjects = (
        args.clean_target_objects
    )
    export_cluster_request.sqlExportOptions.ifExistTargetObjects = (
        args.if_exist_target_objects
    )
  export_cluster_request.gcsDestination = alloydb_messages.GcsDestination()
  export_cluster_request.gcsDestination.uri = args.gcs_uri
  return alloydb_messages.AlloydbProjectsLocationsClustersExportRequest(
      name=cluster_ref.RelativeName(),
      exportClusterRequest=export_cluster_request,
  )


def ConstructImportRequestFromArgs(alloydb_messages, cluster_ref, args):
  """Returns the cluster import request based on args."""
  import_cluster_request = alloydb_messages.ImportClusterRequest()
  import_cluster_request.database = args.database
  import_cluster_request.user = args.user
  import_cluster_request.gcsUri = args.gcs_uri
  if args.csv:
    import_cluster_request.csvImportOptions = (
        alloydb_messages.CsvImportOptions()
    )
    import_cluster_request.csvImportOptions.table = args.table
    if args.columns:
      import_cluster_request.csvImportOptions.columns = args.columns.split(',')
    import_cluster_request.csvImportOptions.fieldDelimiter = (
        args.field_delimiter
    )
    import_cluster_request.csvImportOptions.escapeCharacter = (
        args.escape_character
    )
    import_cluster_request.csvImportOptions.quoteCharacter = (
        args.quote_character
    )
  elif args.sql:
    import_cluster_request.sqlImportOptions = (
        alloydb_messages.SqlImportOptions()
    )
  return alloydb_messages.AlloydbProjectsLocationsClustersImportRequest(
      name=cluster_ref.RelativeName(),
      importClusterRequest=import_cluster_request,
  )


def ConstructMigrateCloudSqlRequestFromArgsAlpha(
    alloydb_messages: types.ModuleType,
    location_ref: resources.Resource,
    args: argparse.Namespace,
) -> messages.Message:
  """Constructs the Migrate Cloud Sql request for Alpha release track.

  Args:
    alloydb_messages: The AlloyDB messages module.
    location_ref: The location reference for the request.
    args: An object that contains the values for the arguments specified in the
      .Args() method.

  Returns:
    The Migrate Cloud Sql request based on args for Alpha release track.
  """
  migrate_cloud_sql_request = alloydb_messages.RestoreFromCloudSQLRequest()
  migrate_cloud_sql_request.cluster = _ConstructClusterForCreateRequestAlpha(
      alloydb_messages, args
  )
  migrate_cloud_sql_request.clusterId = args.cluster
  migrate_cloud_sql_request.cloudsqlBackupRunSource = (
      alloydb_messages.CloudSQLBackupRunSource()
  )
  migrate_cloud_sql_request.cloudsqlBackupRunSource.backupRunId = (
      args.cloud_sql_backup_id
  )
  migrate_cloud_sql_request.cloudsqlBackupRunSource.instanceId = (
      args.cloud_sql_instance_id
  )
  migrate_cloud_sql_request.cloudsqlBackupRunSource.project = (
      args.cloud_sql_project_id
  )

  return alloydb_messages.AlloydbProjectsLocationsClustersRestoreFromCloudSQLRequest(
      parent=location_ref.RelativeName(),
      restoreFromCloudSQLRequest=migrate_cloud_sql_request,
  )


def ConstructMigrateCloudSqlRequestFromArgsBeta(
    alloydb_messages: types.ModuleType,
    location_ref: resources.Resource,
    args: argparse.Namespace,
) -> messages.Message:
  """Constructs the Migrate Cloud Sql request for Beta release track.

  Args:
    alloydb_messages: The AlloyDB messages module.
    location_ref: The location reference for the request.
    args: An object that contains the values for the arguments specified in the
      .Args() method.

  Returns:
    The Migrate Cloud Sql request based on args for Beta release track.
  """
  migrate_cloud_sql_request = alloydb_messages.RestoreFromCloudSQLRequest()
  migrate_cloud_sql_request.cluster = _ConstructClusterForCreateRequestBeta(
      alloydb_messages, args
  )
  migrate_cloud_sql_request.clusterId = args.cluster
  migrate_cloud_sql_request.cloudsqlBackupRunSource = (
      alloydb_messages.CloudSQLBackupRunSource()
  )
  migrate_cloud_sql_request.cloudsqlBackupRunSource.backupRunId = (
      args.cloud_sql_backup_id
  )
  migrate_cloud_sql_request.cloudsqlBackupRunSource.instanceId = (
      args.cloud_sql_instance_id
  )
  migrate_cloud_sql_request.cloudsqlBackupRunSource.project = (
      args.cloud_sql_project_id
  )

  return alloydb_messages.AlloydbProjectsLocationsClustersRestoreFromCloudSQLRequest(
      parent=location_ref.RelativeName(),
      restoreFromCloudSQLRequest=migrate_cloud_sql_request,
  )
