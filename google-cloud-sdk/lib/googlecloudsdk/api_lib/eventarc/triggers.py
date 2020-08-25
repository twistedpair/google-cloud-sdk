# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Utilities for Eventarc Triggers API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.core import resources

_API_NAME = 'eventarc'
_API_VERSION = 'v1beta1'


def GetTriggerURI(resource):
  trigger = resources.REGISTRY.ParseRelativeName(
      resource.name, collection='eventarc.projects.locations.triggers')
  return trigger.SelfLink()


class TriggersClient(object):
  """Client for Triggers service in the Eventarc API."""

  def __init__(self):
    client = apis.GetClientInstance(_API_NAME, _API_VERSION)
    self._messages = client.MESSAGES_MODULE
    self._service = client.projects_locations_triggers
    self._operation_service = client.projects_locations_operations

  def _BuildTriggerMessage(self, trigger_ref, matching_criteria,
                           service_account_ref, destination_run_service_ref,
                           destination_run_path):
    """Builds a Trigger message with the given data."""
    matching_criteria_messages = [
        self._messages.MatchingCriteria(attribute=key, value=value)
        for key, value in matching_criteria.items()
    ]
    service_account_name = service_account_ref.RelativeName(
    ) if service_account_ref else None
    service_message = self._messages.CloudRunService(
        service=destination_run_service_ref.RelativeName(),
        path=destination_run_path)
    destination_message = self._messages.Destination(
        cloudRunService=service_message)
    return self._messages.Trigger(
        name=trigger_ref.RelativeName(),
        matchingCriteria=matching_criteria_messages,
        serviceAccount=service_account_name,
        destination=destination_message)

  def Create(self, trigger_ref, matching_criteria, service_account_ref,
             destination_run_service_ref, destination_run_path):
    """Creates a new Trigger.

    Args:
      trigger_ref: Resource, the Trigger to create.
      matching_criteria: dict, the Trigger's matching criteria.
      service_account_ref: Resource or None, the Trigger's service account.
      destination_run_service_ref: Resource, the Trigger's destination service.
      destination_run_path: str or None, the Trigger's destination path.

    Returns:
      A long-running operation for create.
    """
    trigger_message = self._BuildTriggerMessage(trigger_ref, matching_criteria,
                                                service_account_ref,
                                                destination_run_service_ref,
                                                destination_run_path)
    create_req = self._messages.EventarcProjectsLocationsTriggersCreateRequest(
        parent=trigger_ref.Parent().RelativeName(),
        trigger=trigger_message,
        triggerId=trigger_ref.Name())
    return self._service.Create(create_req)

  def Delete(self, trigger_ref):
    """Deletes a Trigger.

    Args:
      trigger_ref: Resource, the Trigger to delete.

    Returns:
      A long-running operation for delete.
    """
    delete_req = self._messages.EventarcProjectsLocationsTriggersDeleteRequest(
        name=trigger_ref.RelativeName())
    return self._service.Delete(delete_req)

  def Get(self, trigger_ref):
    """Gets a Trigger.

    Args:
      trigger_ref: Resource, the Trigger to get.

    Returns:
      The Trigger message.
    """
    get_req = self._messages.EventarcProjectsLocationsTriggersGetRequest(
        name=trigger_ref.RelativeName())
    return self._service.Get(get_req)

  def List(self, location_ref, limit, page_size):
    """Lists Triggers in a given location.

    Args:
      location_ref: Resource, the location to list Triggers in.
      limit: int or None, the total number of results to return.
      page_size: int, the number of entries in each batch (affects requests
        made, but not the yielded results).

    Returns:
      A generator of Triggers in the location.
    """
    list_req = self._messages.EventarcProjectsLocationsTriggersListRequest(
        parent=location_ref.RelativeName(), pageSize=page_size)
    return list_pager.YieldFromList(
        self._service,
        list_req,
        field='triggers',
        batch_size=page_size,
        limit=limit,
        batch_size_attribute='pageSize')

  def WaitFor(self, operation, delete=False):
    """Waits until the given long-running operation is complete.

    Args:
      operation: the long-running operation to wait for.
      delete: bool, whether the operation is a delete operation.

    Returns:
      The Trigger that is the subject of the operation.
    """
    poller = waiter.CloudOperationPollerNoResources(
        self._operation_service) if delete else waiter.CloudOperationPoller(
            self._service, self._operation_service)
    operation_ref = resources.REGISTRY.Parse(
        operation.name, collection='eventarc.projects.locations.operations')
    message = 'Waiting for operation [{}] to complete'.format(
        operation_ref.Name())
    return waiter.WaitFor(poller, operation_ref, message)
