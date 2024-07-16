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
"""Utility for updating Memorystore Redis clusters."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import encoding
from googlecloudsdk.command_lib.redis import cluster_util
from googlecloudsdk.command_lib.redis import util


class Error(Exception):
  """Exceptions for this module."""


class InvalidTimeOfDayError(Error):
  """Error for passing invalid time of day."""


def AddFieldToUpdateMask(field, patch_request):
  update_mask = patch_request.updateMask
  if update_mask:
    if update_mask.count(field) == 0:
      patch_request.updateMask = update_mask + ',' + field
  else:
    patch_request.updateMask = field
  return patch_request


def AddNewRedisClusterConfigs(cluster_ref, redis_configs_dict, patch_request):
  messages = util.GetMessagesForResource(cluster_ref)
  new_redis_configs = cluster_util.PackageClusterRedisConfig(
      redis_configs_dict, messages
  )
  patch_request.cluster.redisConfigs = new_redis_configs
  patch_request = AddFieldToUpdateMask('redis_configs', patch_request)
  return patch_request


def UpdateReplicaCount(unused_cluster_ref, args, patch_request):
  """Hook to add replica count to the redis cluster update request."""
  if args.IsSpecified('replica_count'):
    patch_request.cluster.replicaCount = args.replica_count
    patch_request = AddFieldToUpdateMask('replica_count', patch_request)
  return patch_request


def UpdateMaintenanceWindowPolicy(unused_cluster_ref, args, patch_request):
  """Hook to update maintenance window policy to the update mask of the request."""
  if (
      args.IsSpecified('maintenance_window_day')
      or args.IsSpecified('maintenance_window_hour')
  ):
    patch_request = AddFieldToUpdateMask('maintenance_window', patch_request)
  return patch_request


def UpdateMaintenanceWindowAny(unused_cluster_ref, args, patch_request):
  """Hook to remove maintenance policy."""
  if args.IsSpecified('maintenance_window_any'):
    patch_request.cluster.maintenancePolicy = None
    patch_request = AddFieldToUpdateMask('maintenance_window', patch_request)
  return patch_request


def UpdateShardCount(unused_cluster_ref, args, patch_request):
  """Hook to add shard count to the redis cluster update request."""
  if args.IsSpecified('shard_count'):
    patch_request.cluster.shardCount = args.shard_count
    patch_request = AddFieldToUpdateMask('shard_count', patch_request)
  return patch_request


def UpdateDeletionProtection(unused_cluster_ref, args, patch_request):
  """Hook to add delete protection to the redis cluster update request."""
  if args.IsSpecified('deletion_protection'):
    patch_request.cluster.deletionProtectionEnabled = args.deletion_protection
    patch_request = AddFieldToUpdateMask(
        'deletion_protection_enabled', patch_request
    )
  return patch_request


def UpdateRedisConfigs(cluster_ref, args, patch_request):
  """Hook to update redis configs to the redis cluster update request."""
  if args.IsSpecified('update_redis_config'):
    config_dict = {}
    if getattr(patch_request.cluster, 'redisConfigs', None):
      config_dict = encoding.MessageToDict(patch_request.cluster.redisConfigs)
    config_dict.update(args.update_redis_config)
    patch_request = AddNewRedisClusterConfigs(
        cluster_ref, config_dict, patch_request
    )
  return patch_request


def RemoveRedisConfigs(cluster_ref, args, patch_request):
  """Hook to remove redis configs to the redis cluster update request."""
  if not getattr(patch_request.cluster, 'redisConfigs', None):
    return patch_request
  if args.IsSpecified('remove_redis_config'):
    config_dict = encoding.MessageToDict(patch_request.cluster.redisConfigs)
    for removed_key in args.remove_redis_config:
      config_dict.pop(removed_key, None)
    patch_request = AddNewRedisClusterConfigs(
        cluster_ref, config_dict, patch_request
    )
  return patch_request


def UpdatePersistenceConfig(unused_cluster_ref, args, patch_request):
  """Hook to add persistence config to the redis cluster update request."""
  if (
      args.IsSpecified('persistence_mode')
      or args.IsSpecified('rdb_snapshot_period')
      or args.IsSpecified('rdb_snapshot_start_time')
      or args.IsSpecified('aof_append_fsync')
  ):
    patch_request = AddFieldToUpdateMask('persistence_config', patch_request)

  # Before update, gcloud will `get` the cluster and overrides the existing
  # persistence config with the input.
  # We can't send both RDB & AOF config to the backend. Explicitly zero out
  # the non selected config so only one mode is sent to backend.
  if patch_request.cluster.persistenceConfig:
    if not args.IsSpecified('rdb_snapshot_period') and not args.IsSpecified(
        'rdb_snapshot_start_time'
    ):
      patch_request.cluster.persistenceConfig.rdbConfig = None
    if not args.IsSpecified('aof_append_fsync'):
      patch_request.cluster.persistenceConfig.aofConfig = None
  return patch_request


def CheckMaintenanceWindowStartTimeField(maintenance_window_start_time):
  if maintenance_window_start_time < 0 or maintenance_window_start_time > 23:
    raise InvalidTimeOfDayError(
        'A valid time of day must be specified (0, 23) hours.'
    )
  return maintenance_window_start_time
