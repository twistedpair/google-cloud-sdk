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
"""Common utility functions to construct compute reservations sub block messages."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import exceptions


def MakeFaultBehavior(messages, fault_behavior):
  """Constructs the fault behavior enum value."""
  if fault_behavior:
    try:
      return messages.ReservationSubBlocksReportFaultyRequestFaultReason.BehaviorValueValuesEnum(
          fault_behavior.upper())
    except TypeError:
      raise exceptions.InvalidArgumentException(
          '--fault-reasons',
          'Invalid fault behavior: {}'.format(fault_behavior))
  return None


def MakeDisruptionSchedule(messages, disruption_schedule):
  """Constructs the disruption schedule enum value."""
  if disruption_schedule:
    try:
      return messages.ReservationSubBlocksReportFaultyRequest.DisruptionScheduleValueValuesEnum(
          disruption_schedule.upper())
    except TypeError:
      raise exceptions.InvalidArgumentException(
          '--disruption-schedule',
          'Invalid disruption schedule: {}'.format(disruption_schedule))
  return None


def MakeFailureComponent(messages, failure_component):
  """Constructs the failure component enum value."""
  if failure_component:
    try:
      return messages.ReservationSubBlocksReportFaultyRequest.FailureComponentValueValuesEnum(
          failure_component.upper())
    except TypeError:
      raise exceptions.InvalidArgumentException(
          '--failure-component',
          'Invalid failure component: {}'.format(failure_component))
  return None
