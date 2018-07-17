# -*- coding: utf-8 -*- #
# Copyright 2017 Google Inc. All Rights Reserved.
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

"""Helpers for constructing messages for instance configs requests."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import exceptions
import six


def GetMode(messages, mode):
  """Returns mode message basing on short user friendly string."""
  enum_class = messages.ManagedInstanceOverrideDiskOverride.ModeValueValuesEnum
  if isinstance(mode, six.string_types):
    return {
        'ro': enum_class.READ_ONLY,
        'rw': enum_class.READ_WRITE,
    }[mode]
  else:
    # handle converting from AttachedDisk.ModeValueValuesEnum
    return enum_class(mode.name)


def GetDiskOverride(messages, stateful_disk, disk_getter):
  """Prepares disk override message, combining with params from the instance."""
  if stateful_disk.get('source'):
    source = stateful_disk.get('source')
    mode = stateful_disk.get('mode', 'rw')
  else:
    disk = disk_getter.get_disk(device_name=stateful_disk.get('device-name'))
    if disk is None:
      if disk_getter.instance_exists:
        error_message = ('[source] must be given while defining stateful disks'
                         ' in instance configs for non existing disks in given'
                         ' instance')
      else:
        error_message = ('[source] must be given while defining stateful disks'
                         ' in instance configs for non existing instances')
      raise exceptions.BadArgumentException('source', error_message)
    source = disk.source
    mode = disk.mode
  return messages.ManagedInstanceOverrideDiskOverride(
      deviceName=stateful_disk.get('device-name'),
      source=source,
      mode=GetMode(messages, mode),
  )


def CallPerInstanceConfigUpdate(holder, igm_ref, per_instance_config_message):
  """Calls proper (zonal or regional) resource for instance config update."""
  messages = holder.client.messages
  if igm_ref.Collection() == 'compute.instanceGroupManagers':
    service = holder.client.apitools_client.instanceGroupManagers
    request = (
        messages.ComputeInstanceGroupManagersUpdatePerInstanceConfigsRequest)(
            instanceGroupManager=igm_ref.Name(),
            instanceGroupManagersUpdatePerInstanceConfigsReq=messages.
            InstanceGroupManagersUpdatePerInstanceConfigsReq(
                perInstanceConfigs=[per_instance_config_message]),
            project=igm_ref.project,
            zone=igm_ref.zone,
        )
    operation_collection = 'compute.zoneOperations'
  elif igm_ref.Collection() == 'compute.regionInstanceGroupManagers':
    service = holder.client.apitools_client.regionInstanceGroupManagers
    request = (
        messages.
        ComputeRegionInstanceGroupManagersUpdatePerInstanceConfigsRequest)(
            instanceGroupManager=igm_ref.Name(),
            regionInstanceGroupManagerUpdateInstanceConfigReq=messages.
            RegionInstanceGroupManagerUpdateInstanceConfigReq(
                perInstanceConfigs=[per_instance_config_message]),
            project=igm_ref.project,
            region=igm_ref.region,
        )
    operation_collection = 'compute.regionOperations'
  else:
    raise ValueError('Unknown reference type {0}'.format(igm_ref.Collection()))

  operation = service.UpdatePerInstanceConfigs(request)
  operation_ref = holder.resources.Parse(
      operation.selfLink, collection=operation_collection)
  return operation_ref


def GetApplyUpdatesToInstancesRequestsZonal(holder, igm_ref, instances):
  """Immediately applies updates to instances (zonal case)."""
  messages = holder.client.messages
  request = messages.InstanceGroupManagersApplyUpdatesRequest(
      instances=instances,
      minimalAction=messages.InstanceGroupManagersApplyUpdatesRequest.
      MinimalActionValueValuesEnum.NONE,
      maximalAction=messages.InstanceGroupManagersApplyUpdatesRequest.
      MaximalActionValueValuesEnum.RESTART)
  return messages.ComputeInstanceGroupManagersApplyUpdatesToInstancesRequest(
      instanceGroupManager=igm_ref.Name(),
      instanceGroupManagersApplyUpdatesRequest=request,
      project=igm_ref.project,
      zone=igm_ref.zone,
  )


def GetApplyUpdatesToInstancesRequestsRegional(holder, igm_ref, instances):
  """Immediately applies updates to instances (regional case)."""
  messages = holder.client.messages
  request = messages.RegionInstanceGroupManagersApplyUpdatesRequest(
      instances=instances,
      minimalAction=messages.RegionInstanceGroupManagersApplyUpdatesRequest.
      MinimalActionValueValuesEnum.NONE,
      maximalAction=messages.RegionInstanceGroupManagersApplyUpdatesRequest.
      MaximalActionValueValuesEnum.RESTART)
  return (
      messages.ComputeRegionInstanceGroupManagersApplyUpdatesToInstancesRequest
  )(
      instanceGroupManager=igm_ref.Name(),
      regionInstanceGroupManagersApplyUpdatesRequest=request,
      project=igm_ref.project,
      region=igm_ref.region,
  )


def CallApplyUpdatesToInstances(holder, igm_ref, instances):
  """Calls proper (zonal or reg.) resource for applying updates to instances."""
  if igm_ref.Collection() == 'compute.instanceGroupManagers':
    operation_collection = 'compute.zoneOperations'
    service = holder.client.apitools_client.instanceGroupManagers
    apply_request = GetApplyUpdatesToInstancesRequestsZonal(
        holder, igm_ref, instances)
  else:
    operation_collection = 'compute.regionOperations'
    service = holder.client.apitools_client.regionInstanceGroupManagers
    apply_request = GetApplyUpdatesToInstancesRequestsRegional(
        holder, igm_ref, instances)
  apply_operation = service.ApplyUpdatesToInstances(apply_request)
  apply_operation_ref = holder.resources.Parse(
      apply_operation.selfLink, collection=operation_collection)
  return apply_operation_ref
