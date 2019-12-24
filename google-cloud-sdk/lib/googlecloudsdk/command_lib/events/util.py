# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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
"""Provides common methods for the Events command surface."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from googlecloudsdk.api_lib.events import trigger
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.command_lib.events import exceptions
from googlecloudsdk.core import resources
from googlecloudsdk.core.util import retry


SOURCE_COLLECTION_NAME = 'run.namespaces.{plural_kind}'


# Max wait time before timing out
_POLLING_TIMEOUT_MS = 60000
# Max wait time between poll retries before timing out
_RETRY_TIMEOUT_MS = 1000


def EventTypeFromTypeString(source_crds, type_string):
  """Returns the matching event type object given a list of source crds."""
  for crd in source_crds:
    for event_type in crd.event_types:
      if type_string == event_type.type:
        return event_type
  raise exceptions.EventTypeNotFound(
      'Unknown event type: {}.'.format(type_string))


def GetSourceRef(name, namespace, source_crd):
  """Returns a resources.Resource from the given source_crd and name."""
  return resources.REGISTRY.Parse(
      name,
      {'namespacesId': namespace},
      SOURCE_COLLECTION_NAME.format(plural_kind=source_crd.source_kind_plural))


def ValidateTrigger(trigger_obj, expected_source_obj, expected_event_type):
  """Validates the given trigger to reference the given source and event type.

  Args:
    trigger_obj: trigger.Trigger, the trigger to validate.
    expected_source_obj: source.Source, the source the trigger should reference.
    expected_event_type: custom_resource_definition.EventTYpe, the event type
      the trigger should reference.

  Raises:
    AssertionError if the trigger does not have matching values.
  """
  source_obj_ref = trigger_obj.dependency
  assert source_obj_ref == expected_source_obj.AsObjectReference()
  try:
    assert trigger_obj.filter_attributes[
        trigger.EVENT_TYPE_FIELD] == expected_event_type.type
  except KeyError:
    raise AssertionError


def WaitForCondition(poller, error_class):
  """Wait for a configuration to be ready in latest revision.

  Args:
    poller: A serverless_operations.ConditionPoller object.
    error_class: Error to raise on timeout failure

  Returns:
    A googlecloudsdk.command_lib.run.condition.Conditions object.

  Raises:
    error_class: Max retry limit exceeded.
  """

  try:
    return waiter.PollUntilDone(
        poller,
        None,
        max_wait_ms=_POLLING_TIMEOUT_MS,
        wait_ceiling_ms=_RETRY_TIMEOUT_MS)
  except retry.RetryException:
    conditions = poller.GetConditions()
    # err.message already indicates timeout. Check ready_cond_type for more
    # information.
    msg = conditions.DescriptiveMessage() if conditions else None
    raise error_class(msg)
