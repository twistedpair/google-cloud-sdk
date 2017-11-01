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
"""Utilities for Cloud Pub/Sub Subscriptions API."""
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import exceptions


DEFAULT_MESSAGE_RETENTION_VALUE = 'default'


class NoFieldsSpecifiedError(exceptions.Error):
  """Error when no fields were specified for a Patch operation."""


def GetClientInstance(no_http=False):
  return apis.GetClientInstance('pubsub', 'v1', no_http=no_http)


def GetMessagesModule(client=None):
  client = client or GetClientInstance()
  return client.MESSAGES_MODULE


class _SubscriptionUpdateSetting(object):
  """Data container class for updating a subscription."""

  def __init__(self, field_name, value):
    self.field_name = field_name
    self.value = value


class SubscriptionsClient(object):
  """Client for subscriptions service in the Cloud Pub/Sub API."""

  def __init__(self, client=None, messages=None):
    self.client = client or GetClientInstance()
    self.messages = messages or GetMessagesModule(client)
    self._service = self.client.projects_subscriptions

  def Ack(self, ack_ids, subscription_ref):
    """Acknowledges one or messages for a Subscription.

    Args:
      ack_ids (list[str]): List of ack ids for the messages being ack'd.
      subscription_ref (Resource): Relative name of the subscription for which
        to ack messages for.
    Returns:
      None:
    """
    ack_req = self.messages.PubsubProjectsSubscriptionsAcknowledgeRequest(
        acknowledgeRequest=self.messages.AcknowledgeRequest(ackIds=ack_ids),
        subscription=subscription_ref.RelativeName())

    return self._service.Acknowledge(ack_req)

  def Create(self, subscription_ref, topic_ref, ack_deadline, push_config=None,
             retain_acked_messages=None, message_retention_duration=None):
    """Creates a Subscription.

    Args:
      subscription_ref (Resource): Resource reference for subscription to be
        created.
      topic_ref (Resource): Resource reference for the associated topic for the
        subscriptions.
      ack_deadline (int): Number of seconds the system will wait for a
        subscriber to ack a message.
      push_config (Message): Message containing the push endpoint for the
        subscription.
      retain_acked_messages (bool): Whether or not to retain acked messages.
      message_retention_duration (int): How long to retained unacked messages.
    Returns:
      Subscription: the created subscription
    """
    subscription = self.messages.Subscription(
        name=subscription_ref.RelativeName(),
        topic=topic_ref.RelativeName(),
        ackDeadlineSeconds=ack_deadline,
        pushConfig=push_config,
        retainAckedMessages=retain_acked_messages,
        messageRetentionDuration=message_retention_duration)

    return self._service.Create(subscription)

  def Delete(self, subscription_ref):
    """Deletes a Subscription.

    Args:
      subscription_ref (Resource): Resource reference for subscription to be
        deleted.
    Returns:
      None:
    """
    delete_req = self.messages.PubsubProjectsSubscriptionsDeleteRequest(
        subscription=subscription_ref.RelativeName())
    return self._service.Delete(delete_req)

  def List(self, project_ref, page_size=100):
    """Lists Subscriptions for a given project.

    Args:
      project_ref (Resource): Resource reference to Project to list
        subscriptions from.
      page_size (int): the number of entries in each batch (affects requests
        made, but not the yielded results).
    Returns:
      A generator of subscriptions in the project.
    """
    list_req = self.messages.PubsubProjectsSubscriptionsListRequest(
        project=project_ref.RelativeName(),
        pageSize=page_size
    )
    return list_pager.YieldFromList(
        self._service, list_req, batch_size=page_size,
        field='subscriptions', batch_size_attribute='pageSize')

  def ModifyAckDeadline(self, subscription_ref, ack_ids, ack_deadline):
    """Modifies the ack deadline for messages for a Subscription.

    Args:
      subscription_ref (Resource): Resource reference for subscription to be
        modified.
      ack_ids (list[str]): List of ack ids to modify.
      ack_deadline (int): The new ack deadline for the messages.
    Returns:
      None:
    """
    mod_req = self.messages.PubsubProjectsSubscriptionsModifyAckDeadlineRequest(
        modifyAckDeadlineRequest=self.messages.ModifyAckDeadlineRequest(
            ackDeadlineSeconds=ack_deadline,
            ackIds=ack_ids),
        subscription=subscription_ref.RelativeName())

    return self._service.ModifyAckDeadline(mod_req)

  def ModifyPushConfig(self, subscription_ref, push_config):
    """Modifies the push endpoint for a Subscription.

    Args:
      subscription_ref (Resource): Resource reference for subscription to be
        modified.
      push_config (Message): The new push endpoint for the Subscription.
    Returns:
      None:
    """
    mod_req = self.messages.PubsubProjectsSubscriptionsModifyPushConfigRequest(
        modifyPushConfigRequest=self.messages.ModifyPushConfigRequest(
            pushConfig=push_config),
        subscription=subscription_ref.RelativeName())
    return self._service.ModifyPushConfig(mod_req)

  def Pull(self, subscription_ref, max_messages):
    """Pulls one or more messages from a Subscription.

    Args:
      subscription_ref (Resource): Resource reference for subscription to be
        pulled from.
      max_messages (int): The maximum number of messages to retrieve.
    Returns:
      PullResponse: proto containing the received messages.
    """
    pull_req = self.messages.PubsubProjectsSubscriptionsPullRequest(
        pullRequest=self.messages.PullRequest(
            maxMessages=max_messages, returnImmediately=True),
        subscription=subscription_ref.RelativeName())
    return self._service.Pull(pull_req)

  def Seek(self, subscription_ref, time=None, snapshot_ref=None):
    """Reset a Subscription's backlog to point to a given time or snapshot.

    Args:
      subscription_ref (Resource): Resource reference for subscription to be
        seeked on.
      time (str): The time to reset to.
      snapshot_ref (Resource): Resource reference to a snapshot..
    Returns:
      None:
    """
    snapshot = snapshot_ref and snapshot_ref.RelativeName()
    seek_req = self.messages.PubsubProjectsSubscriptionsSeekRequest(
        seekRequest=self.messages.SeekRequest(
            snapshot=snapshot, time=time),
        subscription=subscription_ref.RelativeName())
    return self._service.Seek(seek_req)

  def _HandleMessageRetentionUpdate(self, update_setting):
    if update_setting.value == DEFAULT_MESSAGE_RETENTION_VALUE:
      update_setting.value = None

  def Patch(self, subscription_ref, ack_deadline=None, push_config=None,
            retain_acked_messages=None, message_retention_duration=None):
    """Updates a Subscription.

    Args:
      subscription_ref (Resource): Resource reference for subscription to be
        updated.
      ack_deadline (int): Number of seconds the system will wait for a
        subscriber to ack a message.
      push_config (Message): Message containing the push endpoint for the
        subscription.
      retain_acked_messages (bool): Whether or not to retain acked messages.
      message_retention_duration (str): How long to retained unacked messages.
    Returns:
      Subscription: The updated subscription.
    Raises:
      NoFieldsSpecifiedError: if no fields were specified.
    """
    update_settings = [
        _SubscriptionUpdateSetting(
            'ackDeadlineSeconds',
            ack_deadline),
        _SubscriptionUpdateSetting(
            'pushConfig',
            push_config),
        _SubscriptionUpdateSetting(
            'retainAckedMessages',
            retain_acked_messages),
        _SubscriptionUpdateSetting(
            'messageRetentionDuration',
            message_retention_duration),
    ]
    subscription = self.messages.Subscription(
        name=subscription_ref.RelativeName())
    update_mask = []
    for update_setting in update_settings:
      if update_setting.value is not None:
        if update_setting.field_name == 'messageRetentionDuration':
          self._HandleMessageRetentionUpdate(update_setting)
        setattr(subscription, update_setting.field_name, update_setting.value)
        update_mask.append(update_setting.field_name)
    if not update_mask:
      raise NoFieldsSpecifiedError('Must specify at least one field to update.')
    patch_req = self.messages.PubsubProjectsSubscriptionsPatchRequest(
        updateSubscriptionRequest=self.messages.UpdateSubscriptionRequest(
            subscription=subscription,
            updateMask=','.join(update_mask)),
        name=subscription_ref.RelativeName())

    return self._service.Patch(patch_req)
