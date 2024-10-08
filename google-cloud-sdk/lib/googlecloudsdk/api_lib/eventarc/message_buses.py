# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Utilities for Eventarc MessageBuses API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.eventarc import base
from googlecloudsdk.api_lib.eventarc import common
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import resources


class NoFieldsSpecifiedError(exceptions.Error):
  """Error when no fields were specified for a Patch operation."""


def GetMessageBusURI(resource):
  message_buses = resources.REGISTRY.ParseRelativeName(
      resource.name, collection='eventarc.projects.locations.messageBuses'
  )
  return message_buses.SelfLink()


class MessageBusClientV1(base.EventarcClientBase):
  """MessageBus Client for interaction with v1 of Eventarc MessageBuses API."""

  def __init__(self):
    super(MessageBusClientV1, self).__init__(
        common.API_NAME, common.API_VERSION_1, 'message bus'
    )

    # Eventarc Client
    client = apis.GetClientInstance(common.API_NAME, common.API_VERSION_1)

    self._messages = client.MESSAGES_MODULE
    self._service = client.projects_locations_messageBuses

  def Create(self, message_bus_ref, message_bus_message, dry_run=False):
    """Creates a new MessageBus.

    Args:
      message_bus_ref: Resource, the MessageBus to create.
      message_bus_message: MessageBus, the messageBus message that holds
        messageBus' name, crypto key name, etc.
      dry_run: If set, the changes will not be committed, only validated

    Returns:
      A long-running operation for create.
    """
    create_req = (
        self._messages.EventarcProjectsLocationsMessageBusesCreateRequest(
            parent=message_bus_ref.Parent().RelativeName(),
            messageBus=message_bus_message,
            messageBusId=message_bus_ref.Name(),
            validateOnly=dry_run,
        )
    )
    return self._service.Create(create_req)

  def Get(self, message_bus_ref):
    """Gets the requested MessageBus.

    Args:
      message_bus_ref: Resource, the MessageBus to get.

    Returns:
      The MessageBus message.
    """
    get_req = self._messages.EventarcProjectsLocationsMessageBusesGetRequest(
        name=message_bus_ref.RelativeName()
    )
    return self._service.Get(get_req)

  def List(self, location_ref, limit, page_size):
    """List available messageBuses in location.

    Args:
      location_ref: Resource, the location to list MessageBuses in.
      limit: int or None, the total number of results to return.
      page_size: int, the number of entries in each batch (affects requests
        made, but not the yielded results).

    Returns:
      A generator of MessageBuses in the location.
    """
    list_req = self._messages.EventarcProjectsLocationsMessageBusesListRequest(
        parent=location_ref.RelativeName(), pageSize=page_size
    )
    return list_pager.YieldFromList(
        service=self._service,
        request=list_req,
        field='messageBuses',
        limit=limit,
        batch_size=page_size,
        batch_size_attribute='pageSize',
    )

  def Patch(self, message_bus_ref, message_bus_message, update_mask):
    """Updates the specified MessageBus.

    Args:
      message_bus_ref: Resource, the MessageBus to update.
      message_bus_message: MessageBus, the messageBus message that holds
        messageBus' name, crypto key name, etc.
      update_mask: str, a comma-separated list of MessageBus fields to update.

    Returns:
      A long-running operation for update.
    """
    patch_req = (
        self._messages.EventarcProjectsLocationsMessageBusesPatchRequest(
            name=message_bus_ref.RelativeName(),
            messageBus=message_bus_message,
            updateMask=update_mask,
        )
    )
    return self._service.Patch(patch_req)

  def Delete(self, message_bus_ref):
    """Deletes the specified MessageBus.

    Args:
      message_bus_ref: Resource, the MessageBus to delete.

    Returns:
      A long-running operation for delete.
    """
    delete_req = (
        self._messages.EventarcProjectsLocationsMessageBusesDeleteRequest(
            name=message_bus_ref.RelativeName()
        )
    )
    return self._service.Delete(delete_req)

  def BuildMessageBus(self, message_bus_ref, logging_config, crypto_key_name):
    logging_config_enum = None
    if logging_config is not None:
      logging_config_enum = self._messages.LoggingConfig(
          logSeverity=self._messages.LoggingConfig.LogSeverityValueValuesEnum(
              logging_config
          ),
      )
    return self._messages.MessageBus(
        name=message_bus_ref.RelativeName(),
        loggingConfig=logging_config_enum,
        cryptoKeyName=crypto_key_name,
    )

  def BuildUpdateMask(self, logging_config, crypto_key, clear_crypto_key):
    """Builds an update mask for updating a MessageBus.

    Args:
      logging_config: bool, whether to update the logging config.
      crypto_key: bool, whether to update the crypto key.
      clear_crypto_key: bool, whether to clear the crypto key.

    Returns:
      The update mask as a string.


    Raises:
      NoFieldsSpecifiedError: No fields are being updated.
    """
    update_mask = []
    if logging_config:
      update_mask.append('loggingConfig')
    if crypto_key or clear_crypto_key:
      update_mask.append('cryptoKeyName')

    if not update_mask:
      raise NoFieldsSpecifiedError('Must specify at least one field to update.')
    return ','.join(update_mask)

  @property
  def _resource_label_plural(self):
    return 'message-buses'
