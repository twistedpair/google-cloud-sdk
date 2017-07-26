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
"""Utilities Cloud IoT registries API."""
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import exceptions


class NoFieldsSpecifiedError(exceptions.Error):
  """Error when no fields were specified for a Patch operation."""


def GetClientInstance(no_http=False):
  return apis.GetClientInstance('cloudiot', 'v1beta1', no_http=no_http)


def GetMessagesModule(client=None):
  client = client or GetClientInstance()
  return client.MESSAGES_MODULE


class _DeviceRegistryUpdateSetting(object):
  """Small value class holding data for updating a device registry."""

  def __init__(self, field_name, update_mask, value):
    self.field_name = field_name
    self.update_mask = update_mask
    self.value = value


class RegistriesClient(object):
  """Client for registries service in the Cloud IoT API."""

  def __init__(self, client=None, messages=None):
    self.client = client or GetClientInstance()
    self.messages = messages or GetMessagesModule(client)
    self._service = self.client.projects_locations_registries

  @property
  def mqtt_config_enum(self):
    return self.messages.MqttConfig.MqttConfigStateValueValuesEnum

  def Create(self, parent_ref, registry_id,
             pubsub_topic=None, mqtt_config_state=None):
    """Creates a DeviceRegistry.

    Args:
      parent_ref: a Resource reference to a cloudiot.projects.locations
        resource for the parent of this registry.
      registry_id: str, the name of the resource to create.
      pubsub_topic: an optional Resource reference to a pubsub.projects.topics.
        The pubsub topic for notifications on this device registry.
      mqtt_config_state: MqttConfigStateValueValuesEnum, the state of MQTT for
        the registry

    Returns:
      DeviceRegistry: the created registry.
    """
    if pubsub_topic:
      notification_config = self.messages.NotificationConfig(
          pubsubTopicName=pubsub_topic.RelativeName())
    else:
      notification_config = None
    if mqtt_config_state:
      mqtt_config = self.messages.MqttConfig(mqttConfigState=mqtt_config_state)
    else:
      mqtt_config = None
    create_req = self.messages.CloudiotProjectsLocationsRegistriesCreateRequest(
        parent=parent_ref.RelativeName(),
        deviceRegistry=self.messages.DeviceRegistry(
            id=registry_id,
            eventNotificationConfig=notification_config,
            mqttConfig=mqtt_config))

    return self._service.Create(create_req)

  def Delete(self, registry_ref):
    delete_req = self.messages.CloudiotProjectsLocationsRegistriesDeleteRequest(
        name=registry_ref.RelativeName())
    return self._service.Delete(delete_req)

  def Get(self, registry_ref):
    get_req = self.messages.CloudiotProjectsLocationsRegistriesGetRequest(
        name=registry_ref.RelativeName())
    return self._service.Get(get_req)

  def List(self, parent_ref, limit=None, page_size=100):
    """List the device registries in a given location.

    Args:
      parent_ref: a Resource reference to a cloudiot.projects.locations
        resource to list devices for.
      limit: int, the total number of results to return from the API.
      page_size: int, the number of results in each batch from the API.

    Returns:
      A generator of the device registries in the location.
    """
    list_req = self.messages.CloudiotProjectsLocationsRegistriesListRequest(
        parent=parent_ref.RelativeName())
    return list_pager.YieldFromList(
        self._service, list_req, batch_size=page_size, limit=limit,
        field='deviceRegistries', batch_size_attribute='pageSize')

  def Patch(self, registry_ref,
            pubsub_topic=None, mqtt_config_state=None):
    """Updates a DeviceRegistry.

    Any fields not specified will not be updated; at least one field must be
    specified.

    Args:
      registry_ref: a Resource reference to a
        cloudiot.projects.locations.registries resource.
      pubsub_topic: an optional Resource reference to a pubsub.projects.topic.
        The pubsub topic for notifications on this device registry.
      mqtt_config_state: MqttConfigStateValueValuesEnum, the state of MQTT for
        the registry

    Returns:
      DeviceRegistry: the created registry.

    Raises:
      NoFieldsSpecifiedError: if no fields were specified.
    """
    registry = self.messages.DeviceRegistry()
    if pubsub_topic:
      notification_config = self.messages.NotificationConfig(
          pubsubTopicName=pubsub_topic.RelativeName())
    else:
      notification_config = None
    if mqtt_config_state:
      mqtt_config = self.messages.MqttConfig(mqttConfigState=mqtt_config_state)
    else:
      mqtt_config = None
    device_registry_update_settings = [
        _DeviceRegistryUpdateSetting(
            'eventNotificationConfig',
            'device_registry.event_notification_config.pubsub_topic_name',
            notification_config),
        _DeviceRegistryUpdateSetting(
            'mqttConfig',
            'device_registry.mqtt_config.mqtt_config_state',
            mqtt_config)
    ]
    update_mask = []
    for update_setting in device_registry_update_settings:
      if update_setting.value is not None:
        setattr(registry, update_setting.field_name, update_setting.value)
        update_mask.append(update_setting.update_mask)
    if not update_mask:
      raise NoFieldsSpecifiedError('Must specify at least one field to update.')
    patch_req = self.messages.CloudiotProjectsLocationsRegistriesPatchRequest(
        deviceRegistry=registry,
        name=registry_ref.RelativeName(),
        updateMask=','.join(update_mask))

    return self._service.Patch(patch_req)

  def SetIamPolicy(self, registry_ref, set_iam_policy_request):
    """Sets an IAM policy on a DeviceRegistry.

    Args:
      registry_ref: a Resource reference to a
        cloudiot.projects.locations.registries resource.
      set_iam_policy_request: A SetIamPolicyRequest which contains the Policy to
        add.

    Returns:
      Policy: the added policy.
    """
    set_req = (
        self.messages.CloudiotProjectsLocationsRegistriesSetIamPolicyRequest(
            resource=registry_ref.RelativeName(),
            setIamPolicyRequest=set_iam_policy_request))
    return self._service.SetIamPolicy(set_req)

  def GetIamPolicy(self, registry_ref):
    """Gets the IAM policy for a DeviceRegistry.

    Args:
      registry_ref: a Resource reference to a
        cloudiot.projects.locations.registries resource.

    Returns:
      Policy: the policy for the device registry.
    """
    get_req = (
        self.messages.CloudiotProjectsLocationsRegistriesGetIamPolicyRequest(
            resource=registry_ref.RelativeName()))
    return self._service.GetIamPolicy(get_req)
