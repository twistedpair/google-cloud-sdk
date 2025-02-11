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
"""Util functions for Cloud Run v2 conditions."""

from typing import Sequence

from googlecloudsdk.generated_clients.gapic_clients.run_v2.types import condition as condition_objects


_ready_condition_type = 'Ready'


def IsConditionReady(condition: condition_objects.Condition):
  return (
      condition.state == condition_objects.Condition.State.CONDITION_SUCCEEDED
  )


def IsConditionFailed(condition: condition_objects.Condition):
  return condition.state == condition_objects.Condition.State.CONDITION_FAILED


def _GetReadyCondition(conditions: Sequence[condition_objects.Condition]):
  for condition in conditions:
    if condition.type == _ready_condition_type:
      return condition
  return None


def GetTerminalCondition(resource):
  """Returns the terminal condition of a resource.

  Args:
    resource: A Cloud Run v2 resource to get the terminal condition of.

  Returns:
    A condition object representing the terminal condition of the resource, or
    None if the resource does not have a terminal condition.
  """
  return (
      resource.terminal_condition
      if hasattr(resource, 'terminal_condition')
      else _GetReadyCondition(resource.conditions)
  )
