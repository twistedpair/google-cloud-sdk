# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Common utility functions to consturct compute future reservations message."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.compute.reservations import util as reservation_util
from googlecloudsdk.core.util import times


def MakeFutureReservationMessageFromArgs(messages, resources, args,
                                         future_reservation_ref):
  """Construct future reservation message from args passed in."""
  local_ssds = reservation_util.MakeLocalSsds(messages,
                                              getattr(args, 'local_ssd', None))
  accelerators = reservation_util.MakeGuestAccelerators(
      messages, getattr(args, 'accelerator', None))
  allocated_instance_properties = MakeAllocatedInstanceProperties(
      messages, args.machine_type, args.min_cpu_platform, local_ssds,
      accelerators, getattr(args, 'location_hint', None),
      getattr(args, 'maintenance_freeze_duration', None),
      getattr(args, 'maintenance_interval', None))
  source_instance_template_ref = (
      reservation_util.ResolveSourceInstanceTemplate(args, resources)
      if getattr(args, 'source_instance_template', None)
      else None
  )
  sku_properties = MakeSpecificSKUPropertiesMessage(
      messages,
      allocated_instance_properties,
      args.total_count,
      source_instance_template_ref,
  )
  time_window = MakeTimeWindowMessage(messages, args.start_time,
                                      getattr(args, 'end_time', None),
                                      getattr(args, 'duration', None))
  share_settings = MakeShareSettings(messages, args,
                                     getattr(args, 'share_setting', None))
  planning_status = MakePlanningStatus(messages,
                                       getattr(args, 'planning_status', None))

  enable_auto_delete_reservations = None
  if args.IsSpecified('auto_delete_auto_created_reservations'):
    enable_auto_delete_reservations = getattr(
        args, 'auto_delete_auto_created_reservations'
    )

  auto_created_reservations_delete_time = None
  if args.IsSpecified('auto_created_reservations_delete_time'):
    auto_created_reservations_delete_time = getattr(
        args, 'auto_created_reservations_delete_time'
    )
  auto_created_reservations_duration = None
  if args.IsSpecified('auto_created_reservations_duration'):
    auto_created_reservations_duration = getattr(
        args, 'auto_created_reservations_duration'
    )

  require_specific_reservation = getattr(
      args, 'require_specific_reservation', None
  )

  reservation_name = getattr(args, 'reservation_name', None)

  deployment_type = None
  if args.IsKnownAndSpecified('deployment_type'):
    deployment_type = MakeDeploymentType(messages,
                                         getattr(args, 'deployment_type', None))

  commitment_info = MakeCommitmentInfo(messages, args)
  instance_termination_action = None
  if args.IsKnownAndSpecified('instance_termination_action'):
    instance_termination_action = MakeInstanceTerminationAction(
        messages, getattr(args, 'instance_termination_action', None)
    )
  scheduling_type = None
  if args.IsKnownAndSpecified('scheduling_type'):
    scheduling_type = MakeSchedulingType(
        messages, getattr(args, 'scheduling_type', None)
    )
  enable_opportunistic_maintenance = None
  if args.IsKnownAndSpecified('enable_opportunistic_maintenance'):
    enable_opportunistic_maintenance = getattr(
        args, 'enable_opportunistic_maintenance'
    )

  return MakeFutureReservationMessage(
      messages,
      future_reservation_ref.Name(),
      sku_properties,
      time_window,
      share_settings,
      planning_status,
      enable_auto_delete_reservations,
      auto_created_reservations_delete_time,
      auto_created_reservations_duration,
      require_specific_reservation,
      reservation_name,
      deployment_type,
      commitment_info,
      instance_termination_action,
      scheduling_type,
      enable_opportunistic_maintenance,
  )


def MakeAllocatedInstanceProperties(messages,
                                    machine_type,
                                    min_cpu_platform,
                                    local_ssds,
                                    accelerators,
                                    location_hint=None,
                                    freeze_duration=None,
                                    freeze_interval=None):
  """Constructs an instance propteries for reservations message object."""
  prop_msgs = (
      messages.AllocationSpecificSKUAllocationReservedInstanceProperties)
  instance_properties = prop_msgs(
      machineType=machine_type,
      guestAccelerators=accelerators,
      minCpuPlatform=min_cpu_platform,
      localSsds=local_ssds)
  if location_hint:
    instance_properties.locationHint = location_hint
  if freeze_duration:
    instance_properties.maintenanceFreezeDurationHours = freeze_duration // 3600
  if freeze_interval:
    instance_properties.maintenanceInterval = (
        messages.AllocationSpecificSKUAllocationReservedInstanceProperties
        .MaintenanceIntervalValueValuesEnum(freeze_interval))
  return instance_properties


def MakeSpecificSKUPropertiesMessage(
    messages,
    instance_properties,
    total_count,
    source_instance_template_ref=None,
):
  """Constructs a specific sku properties message object."""
  properties = None
  source_instance_template_url = None
  if source_instance_template_ref:
    source_instance_template_url = source_instance_template_ref.SelfLink()
  else:
    properties = instance_properties
  return messages.FutureReservationSpecificSKUProperties(
      totalCount=total_count,
      sourceInstanceTemplate=source_instance_template_url,
      instanceProperties=properties)


def MakeTimeWindowMessage(messages, start_time, end_time, duration):
  """Constructs the time window message object."""
  if end_time:
    return messages.FutureReservationTimeWindow(
        startTime=start_time, endTime=end_time)
  else:
    return messages.FutureReservationTimeWindow(
        startTime=start_time, duration=messages.Duration(seconds=duration))


def MakeShareSettings(messages, args, setting_configs):
  """Constructs the share settings message object."""
  if setting_configs:
    if setting_configs == 'local':
      if args.IsSpecified('share_with'):
        raise exceptions.InvalidArgumentException(
            '--share_with',
            'The scope this reservation is to be shared with must not be '
            'specified with share setting local.')
      return messages.ShareSettings(shareType=messages.ShareSettings
                                    .ShareTypeValueValuesEnum.LOCAL)
    if setting_configs == 'projects':
      if not args.IsSpecified('share_with'):
        raise exceptions.InvalidArgumentException(
            '--share_with',
            'The projects this reservation is to be shared with must be '
            'specified.')
      return messages.ShareSettings(
          shareType=messages.ShareSettings.ShareTypeValueValuesEnum
          .SPECIFIC_PROJECTS,
          projects=getattr(args, 'share_with', None))
  else:
    return None


def MakePlanningStatus(messages, planning_status):
  """Constructs the planning status enum value."""
  if planning_status:
    if planning_status == 'SUBMITTED':
      return messages.FutureReservation.PlanningStatusValueValuesEnum.SUBMITTED
  return None


def MakeDeploymentType(messages, deployment_type):
  """Constructs the deployment type enum value."""
  if deployment_type:
    if deployment_type == 'DENSE':
      return messages.FutureReservation.DeploymentTypeValueValuesEnum.DENSE
    if deployment_type == 'FLEXIBLE':
      return messages.FutureReservation.DeploymentTypeValueValuesEnum.FLEXIBLE
  return None


def MakeCommitmentInfo(messages, args):
  """Constructs the commitment info message object."""
  commitment_name = getattr(args, 'commitment_name', None)
  commitment_plan = None
  if args.IsKnownAndSpecified('commitment_plan'):
    commitment_plan = MakeCommitmentPlan(messages,
                                         getattr(args, 'commitment_plan', None))
  previous_commitment_terms = None
  if args.IsKnownAndSpecified('previous_commitment_terms'):
    previous_commitment_terms = MakePreviousCommitmentTerms(
        messages, getattr(args, 'previous_commitment_terms', None)
    )

  if any([commitment_name, commitment_plan, previous_commitment_terms]):
    return messages.FutureReservationCommitmentInfo(
        commitmentName=commitment_name,
        commitmentPlan=commitment_plan,
        previousCommitmentTerms=previous_commitment_terms,
    )
  return None


def MakeCommitmentPlan(messages, commitment_plan):
  """Constructs the commitment plan enum value."""
  if commitment_plan:
    if commitment_plan == 'TWELVE_MONTH':
      return (messages.FutureReservationCommitmentInfo.CommitmentPlanValueValuesEnum.
              TWELVE_MONTH)
    if commitment_plan == 'THIRTY_SIX_MONTH':
      return (messages.FutureReservationCommitmentInfo.CommitmentPlanValueValuesEnum
              .THIRTY_SIX_MONTH)
  return None


def MakePreviousCommitmentTerms(messages, previous_commitment_terms):
  """Constructs the previous commitment terms enum value."""
  if previous_commitment_terms:
    if previous_commitment_terms == 'EXTEND':
      return (messages.FutureReservationCommitmentInfo.PreviousCommitmentTermsValueValuesEnum
              .EXTEND)
  return None


def MakeInstanceTerminationAction(messages, instance_termination_action):
  """Constructs the instance_termination_action enum value."""
  if instance_termination_action:
    if instance_termination_action == 'DELETE':
      return (messages.FutureReservation
              .InstanceTerminationActionValueValuesEnum.DELETE)
    if instance_termination_action == 'STOP':
      return (messages.FutureReservation
              .InstanceTerminationActionValueValuesEnum.STOP)
  return None


def MakeSchedulingType(messages, scheduling_type):
  """Constructs the scheduling type enum value."""
  if scheduling_type:
    if scheduling_type == 'GROUPED':
      return messages.FutureReservation.SchedulingTypeValueValuesEnum.GROUPED
    if scheduling_type == 'INDEPENDENT':
      return (messages.FutureReservation.SchedulingTypeValueValuesEnum
              .INDEPENDENT)
  return None


def MakeFutureReservationMessage(
    messages,
    future_reservation_name,
    sku_properties,
    time_window,
    share_settings,
    planning_status,
    enable_auto_delete_reservations=None,
    auto_created_reservations_delete_time=None,
    auto_created_reservations_duration=None,
    require_specific_reservation=None,
    reservation_name=None,
    deployment_type=None,
    commitment_info=None,
    instance_termination_action=None,
    scheduling_type=None,
    enable_opportunistic_maintenance=None,
):
  """Constructs a future reservation message object."""
  future_reservation_message = messages.FutureReservation(
      name=future_reservation_name,
      specificSkuProperties=sku_properties,
      timeWindow=time_window,
      planningStatus=planning_status)
  if share_settings:
    future_reservation_message.shareSettings = share_settings

  if enable_auto_delete_reservations is not None:
    future_reservation_message.autoDeleteAutoCreatedReservations = (
        enable_auto_delete_reservations
    )

  if auto_created_reservations_delete_time is not None:
    future_reservation_message.autoCreatedReservationsDeleteTime = (
        times.FormatDateTime(auto_created_reservations_delete_time)
    )
  if auto_created_reservations_duration is not None:
    future_reservation_message.autoCreatedReservationsDuration = (
        messages.Duration(seconds=auto_created_reservations_duration)
    )
  if require_specific_reservation is not None:
    future_reservation_message.specificReservationRequired = (
        require_specific_reservation
    )

  if reservation_name is not None:
    future_reservation_message.reservationName = reservation_name
  if deployment_type is not None:
    future_reservation_message.deploymentType = deployment_type
  if commitment_info is not None:
    future_reservation_message.commitmentInfo = commitment_info
  if instance_termination_action is not None:
    future_reservation_message.instanceTerminationAction = (
        instance_termination_action
    )
  if scheduling_type is not None:
    future_reservation_message.schedulingType = scheduling_type
  if enable_opportunistic_maintenance is not None:
    future_reservation_message.enableOpportunisticMaintenance = (
        enable_opportunistic_maintenance
    )
  return future_reservation_message
