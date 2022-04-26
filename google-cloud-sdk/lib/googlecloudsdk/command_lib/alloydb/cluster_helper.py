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


def ConstructPatchRequestFromArgs(alloydb_messages, cluster_ref, args):
  """Returns the cluster patch request based on args."""
  update_masks = []
  cluster = alloydb_messages.Cluster()

  backup_policy_mask = 'automated_backup_policy'
  backup_policy = alloydb_messages.AutomatedBackupPolicy()
  if args.disable_automated_backup:
    backup_policy.enabled = False
    cluster.automatedBackupPolicy = backup_policy
    update_masks.append(backup_policy_mask)
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
      backup_policy.backupWindow = '{}s'.format(
          args.automated_backup_window)
    backup_policy.location = args.region
    cluster.automatedBackupPolicy = backup_policy
    update_masks.append(backup_policy_mask)
  elif args.clear_automated_backup:
    update_masks.append(backup_policy_mask)

  return alloydb_messages.AlloydbProjectsLocationsClustersPatchRequest(
      name=cluster_ref.RelativeName(),
      cluster=cluster,
      updateMask=','.join(update_masks))
