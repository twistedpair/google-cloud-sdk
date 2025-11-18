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
"""Utility functions for advice."""

from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import times


def GetComputeAdviceCalendarModeRequest(args, messages):
  """Helper function to get the compute advice calendar mode request."""

  calendar_mode_advice_request = GetCalendarModeAdviceRequest(args, messages)

  project = properties.VALUES.core.project.GetOrFail()

  # Use the region specified in the args, else fall back to the compute
  # region property.
  region = args.region or properties.VALUES.compute.region.Get()

  return messages.ComputeAdviceCalendarModeRequest(
      calendarModeAdviceRequest=calendar_mode_advice_request,
      project=project,
      region=region,
  )


def GetCalendarModeAdviceRequest(args, messages):
  """Helper function to get the calendar mode advice request."""

  future_resources_spec = messages.FutureResourcesSpec()

  if args.deployment_type:
    future_resources_spec.deploymentType = arg_utils.ChoiceToEnum(
        args.deployment_type,
        messages.FutureResourcesSpec.DeploymentTypeValueValuesEnum,
    )

  if args.location_policy:
    future_resources_spec.locationPolicy = GetLocationPolicy(args, messages)

  future_resources_spec.targetResources = GetTargetResources(args, messages)
  future_resources_spec.timeRangeSpec = GetTimeRangeSpec(args, messages)

  future_resources_specs_value = messages.CalendarModeAdviceRequest.FutureResourcesSpecsValue(
      additionalProperties=[
          messages.CalendarModeAdviceRequest.FutureResourcesSpecsValue.AdditionalProperty(
              key='spec', value=future_resources_spec
          )
      ]
  )

  return messages.CalendarModeAdviceRequest(
      futureResourcesSpecs=future_resources_specs_value
  )


def GetLocationPolicy(args, messages):
  """Helper function to get the location policy."""

  if not args.location_policy:
    return None

  locations = []
  for zone, policy in args.location_policy.items():
    zone_policy = arg_utils.ChoiceToEnum(
        policy,
        messages.FutureResourcesSpecLocationPolicyLocation.PreferenceValueValuesEnum,
    )
    locations.append(
        messages.FutureResourcesSpecLocationPolicy.LocationsValue.AdditionalProperty(
            key='zones/{}'.format(zone),
            value=messages.FutureResourcesSpecLocationPolicyLocation(
                preference=zone_policy
            ),
        )
    )

  return messages.FutureResourcesSpecLocationPolicy(
      locations=messages.FutureResourcesSpecLocationPolicy.LocationsValue(
          additionalProperties=locations
      )
  )


def GetSkuResources(args, messages):
  """Helper function to get the specific SKU resources."""

  specific_sku_resources = messages.FutureResourcesSpecSpecificSKUResources()

  if args.vm_count:
    specific_sku_resources.instanceCount = args.vm_count

  if args.machine_type:
    specific_sku_resources.machineType = args.machine_type

  if args.local_ssd:
    local_ssd_partitions = []
    for ssd in args.local_ssd:
      partition = messages.FutureResourcesSpecLocalSsdPartition(
          diskSizeGb=ssd['size']
      )
      interface_str = ssd.get('interface')
      if interface_str:
        interface = messages.FutureResourcesSpecLocalSsdPartition.DiskInterfaceValueValuesEnum(
            interface_str
        )
        partition.diskInterface = interface
      local_ssd_partitions.append(partition)
    specific_sku_resources.localSsdPartitions = local_ssd_partitions

  return specific_sku_resources


def GetVmFamily(tpu_version, messages):
  """Helper function to get the VM family."""

  # Static mapping of TPU version to VM family.
  vm_family = (
      messages.FutureResourcesSpecAggregateResources.VmFamilyValueValuesEnum
  )

  # This mapping should be in sync with the future_reservations mapping.
  tpu_version_to_vm_family = {
      'V5E': vm_family.VM_FAMILY_CLOUD_TPU_LITE_POD_SLICE_CT5LP,
      'V5P': vm_family.VM_FAMILY_CLOUD_TPU_POD_SLICE_CT5P,
      'V6E': vm_family.VM_FAMILY_CLOUD_TPU_LITE_POD_SLICE_CT6E,
      'TPU7X': vm_family.VM_FAMILY_CLOUD_TPU_POD_SLICE_TPU7X,
  }

  if tpu_version not in tpu_version_to_vm_family:
    raise exceptions.InvalidArgumentException(
        '--tpu-version',
        'Must specify a valid TPU version ({})'.format(
            ', '.join(tpu_version_to_vm_family.keys())
        ),
    )

  return tpu_version_to_vm_family[tpu_version]


def GetAggregateResources(args, messages):
  """Helper function to get the aggregate resources."""

  aggregate_resources = messages.FutureResourcesSpecAggregateResources()

  if args.chip_count:
    aggregate_resources.acceleratorCount = args.chip_count

  if args.tpu_version:
    aggregate_resources.vmFamily = GetVmFamily(args.tpu_version, messages)

  if args.workload_type:
    aggregate_resources.workloadType = arg_utils.ChoiceToEnum(
        args.workload_type,
        messages.FutureResourcesSpecAggregateResources.WorkloadTypeValueValuesEnum,
    )

  return aggregate_resources


def GetTargetResources(args, messages):
  """Helper function to get the target resources."""

  future_resources_spec_target_resources = (
      messages.FutureResourcesSpecTargetResources()
  )

  # User should specify either SKU or aggregate resources. No need to check
  # here, since gcloud CLI will validate this elarlier.
  # SKU(GPUs) resources.
  if args.machine_type:
    future_resources_spec_target_resources.specificSkuResources = (
        GetSkuResources(args, messages)
    )

  # Aggregate resources.
  if args.tpu_version:
    future_resources_spec_target_resources.aggregateResources = (
        GetAggregateResources(args, messages)
    )

  return future_resources_spec_target_resources


def GetTimeRangeSpec(args, messages):
  """Helper function to get the time ranges."""
  flexible_time_range = messages.FlexibleTimeRange()

  # Start time range.
  if args.start_time_range:
    start_time_from = args.start_time_range.get('from', None)
    if start_time_from is not None:
      flexible_time_range.startTimeNotEarlierThan = times.FormatDateTime(
          start_time_from
      )
    start_time_to = args.start_time_range.get('to', None)
    if start_time_to is not None:
      flexible_time_range.startTimeNotLaterThan = times.FormatDateTime(
          start_time_to
      )

  # End time range.
  if args.end_time_range:
    end_time_from = args.end_time_range.get('from', None)
    if end_time_from is not None:
      flexible_time_range.endTimeNotEarlierThan = times.FormatDateTime(
          end_time_from
      )
    end_time_to = args.end_time_range.get('to', None)
    if end_time_to is not None:
      flexible_time_range.endTimeNotLaterThan = times.FormatDateTime(
          end_time_to
      )

  # Duration range.
  if args.duration_range:
    max_duration = args.duration_range.get('max', None)
    if max_duration is not None:
      flexible_time_range.maxDuration = f'{max_duration}s'
    min_duration = args.duration_range.get('min', None)
    if min_duration is not None:
      flexible_time_range.minDuration = f'{min_duration}s'

  return flexible_time_range
