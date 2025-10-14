# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Constants shared across Cloud SQL commands."""

# A list of flags that can be overridden from the source instance when creating
# a new Cloud SQL instance via a backup restore or PITR operation.
TARGET_INSTANCE_OVERRIDE_FLAGS = (
    # go/keep-sorted start
    'activation_policy',
    'active_directory_dns_servers',
    'active_directory_domain',
    'active_directory_mode',
    'active_directory_organizational_unit',
    'active_directory_secret_manager_key',
    'allowed_psc_projects',
    'assign_ip',
    'audit_bucket_path',
    'authorized_networks',
    'availability_type',
    'backup',
    'backup_location',
    'backup_start_time',
    'clear_active_directory',
    'clear_active_directory_dns_servers',
    'clear_disk_encryption',
    'clear_network',
    'collation',
    'connector_enforcement',
    'cpu',
    'database_version',
    'deletion_protection',
    'deny_maintenance_period_end_date',
    'deny_maintenance_period_start_date',
    'deny_maintenance_period_time',
    'disk_encryption_key',
    'disk_encryption_key_keyring',
    'disk_encryption_key_location',
    'disk_encryption_key_project',
    'edition',
    'enable_bin_log',
    'enable_data_cache',
    'enable_google_ml_integration',
    'enable_google_private_path',
    'enable_point_in_time_recovery',
    'enable_private_service_connect',
    'failover_replica_name',
    'final_backup',
    'final_backup_retention_days',
    'insights_config_query_insights_enabled',
    'insights_config_query_plans_per_minute',
    'insights_config_query_string_length',
    'insights_config_record_application_tags',
    'insights_config_record_client_address',
    'maintenance_release_channel',
    'maintenance_window_day',
    'maintenance_window_hour',
    'memory',
    'network',
    'psc_auto_connections',
    'region',
    'require_ssl',
    'retain_backups_on_delete',
    'retained_backups_count',
    'retained_transaction_log_days',
    'server_ca_mode',
    'ssl_mode',
    'storage_auto_increase',
    'storage_provisioned_iops',
    'storage_provisioned_throughput',
    'storage_size',
    'storage_type',
    'tags',
    'tier',
    'time_zone',
    'timeout',
    # go/keep-sorted end
)

# 1h, based off of the max time it usually takes to create a SQL instance.
INSTANCE_CREATION_TIMEOUT_SECONDS = 3600
