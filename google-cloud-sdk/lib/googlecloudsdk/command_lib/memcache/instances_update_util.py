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
"""Utilities for `gcloud memcache instances update` commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import encoding
from googlecloudsdk.api_lib import memcache
from googlecloudsdk.command_lib.memcache import instances_util


def ChooseUpdateMethod(unused_ref, args):
  if args.IsSpecified('parameters'):
    return 'updateParameters'
  return 'patch'


def AddFieldToUpdateMask(update_mask, field):
  if field not in update_mask:
    update_mask.append(field)


def CreateUpdateRequest(ref, args):
  """Returns an Update or UpdateParameters request depending on the args given."""
  messages = memcache.Messages(ref.GetCollectionInfo().api_version)
  mask = []
  instance = messages.Instance()
  maintenance_policy = _GetMaintenancePolicy(messages)
  weekly_maintenance_window = messages.WeeklyMaintenanceWindow()
  start_time = messages.TimeOfDay()
  if args.IsSpecified('maintenance_window_day'):
    AddFieldToUpdateMask(mask, 'maintenancePolicy')
    weekly_maintenance_window.day = messages.WeeklyMaintenanceWindow.DayValueValuesEnum(
        args.maintenance_window_day.upper())
  if args.IsSpecified('maintenance_window_start_time'):
    AddFieldToUpdateMask(mask, 'maintenancePolicy')
    start_time.hours = instances_util.CheckMaintenanceWindowStartTimeField(
        int(args.maintenance_window_start_time))
    weekly_maintenance_window.startTime = start_time
  if args.IsSpecified('maintenance_window_duration'):
    AddFieldToUpdateMask(mask, 'maintenancePolicy')
    weekly_maintenance_window.duration = instances_util.ConvertDurationToJsonFormat(
        int(args.maintenance_window_duration))
  if 'maintenancePolicy' in mask:
    maintenance_policy.weeklyMaintenanceWindow = [weekly_maintenance_window]
    instance.maintenancePolicy = maintenance_policy
  if args.IsSpecified('maintenance_window_any'):
    AddFieldToUpdateMask(mask, 'maintenancePolicy')
    instance.maintenancePolicy = None

  if args.IsSpecified('parameters'):
    params = encoding.DictToMessage(args.parameters,
                                    messages.MemcacheParameters.ParamsValue)
    parameters = messages.MemcacheParameters(params=params)
    param_req = messages.UpdateParametersRequest(
        updateMask='params', parameters=parameters)
    request = (
        messages.MemcacheProjectsLocationsInstancesUpdateParametersRequest(
            name=ref.RelativeName(), updateParametersRequest=param_req))
  else:
    if args.IsSpecified('display_name'):
      AddFieldToUpdateMask(mask, 'displayName')
      instance.displayName = args.display_name
    if args.IsSpecified('node_count'):
      AddFieldToUpdateMask(mask, 'nodeCount')
      instance.nodeCount = args.node_count
    if args.IsSpecified('labels'):
      AddFieldToUpdateMask(mask, 'labels')
      instance.labels = messages.Instance.LabelsValue(
          additionalProperties=args.labels)
    update_mask = ','.join(mask)
    request = (
        messages.MemcacheProjectsLocationsInstancesPatchRequest(
            name=ref.RelativeName(), instance=instance, updateMask=update_mask))

  return request


def _GetMaintenancePolicy(message_module):
  """Returns a maintenance policy of the appropriate version."""
  if hasattr(message_module, 'GoogleCloudMemcacheV1beta2MaintenancePolicy'):
    return message_module.GoogleCloudMemcacheV1beta2MaintenancePolicy()
  elif hasattr(message_module, 'GoogleCloudMemcacheV1MaintenancePolicy'):
    return message_module.GoogleCloudMemcacheV1MaintenancePolicy()

  raise AttributeError('No MaintenancePolicy found for version V1 or V1beta2.')
