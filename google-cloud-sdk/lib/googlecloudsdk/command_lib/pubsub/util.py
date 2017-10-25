# Copyright 2015 Google Inc. All Rights Reserved.
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
"""A library that is used to support Cloud Pub/Sub commands."""
from googlecloudsdk.command_lib.projects import util as projects_util
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.resource import resource_projector

# Maximum number of results that can be passed in pageSize to list operations.
MAX_LIST_RESULTS = 10000

# Collection for various subcommands.
TOPICS_COLLECTION = 'pubsub.projects.topics'
TOPICS_PUBLISH_COLLECTION = 'pubsub.topics.publish'
SNAPSHOTS_COLLECTION = 'pubsub.projects.snapshots'
SNAPSHOTS_LIST_COLLECTION = 'pubsub.snapshots.list'
SUBSCRIPTIONS_COLLECTION = 'pubsub.projects.subscriptions'
SUBSCRIPTIONS_ACK_COLLECTION = 'pubsub.subscriptions.ack'
SUBSCRIPTIONS_LIST_COLLECTION = 'pubsub.subscriptions.list'
SUBSCRIPTIONS_MOD_ACK_COLLECTION = 'pubsub.subscriptions.mod_ack'
SUBSCRIPTIONS_MOD_CONFIG_COLLECTION = 'pubsub.subscriptions.mod_config'
SUBSCRIPTIONS_PULL_COLLECTION = 'pubsub.subscriptions.pull'
SUBSCRIPTIONS_SEEK_COLLECTION = 'pubsub.subscriptions.seek'


class RequestsFailedError(exceptions.Error):
  """Indicates that some requests to the API have failed."""

  def __init__(self, requests, action):
    super(RequestsFailedError, self).__init__(
        'Failed to {action} the following: [{requests}].'.format(
            action=action, requests=','.join(requests)))


def ParseSnapshot(snapshot_name, project_id=''):
  project_id = _GetProject(project_id)
  return resources.REGISTRY.Parse(snapshot_name,
                                  params={'projectsId': project_id},
                                  collection=SNAPSHOTS_COLLECTION)


def ParseSubscription(subscription_name, project_id=''):
  project_id = _GetProject(project_id)
  return resources.REGISTRY.Parse(subscription_name,
                                  params={'projectsId': project_id},
                                  collection=SUBSCRIPTIONS_COLLECTION)


def ParseTopic(topic_name, project_id=''):
  project_id = _GetProject(project_id)
  return resources.REGISTRY.Parse(topic_name,
                                  params={'projectsId': project_id},
                                  collection=TOPICS_COLLECTION)


def ParseProject(project_id=None):
  project_id = _GetProject(project_id)
  return projects_util.ParseProject(project_id)


def _GetProject(project_id):
  return project_id or properties.VALUES.core.project.Get(required=True)


def SnapshotUriFunc(snapshot):
  return ParseSnapshot(snapshot['name']).SelfLink()


def SubscriptionUriFunc(subscription):
  return ParseSubscription(
      subscription['subscriptionId'], subscription['projectId']).SelfLink()


def TopicUriFunc(topic):
  return ParseTopic(topic['topic']).SelfLink()


# TODO(b/32276674): Remove the use of custom *DisplayDict's.
def TopicDisplayDict(topic):
  """Creates a serializable from a Cloud Pub/Sub Topic operation for display.

  Args:
    topic: (Cloud Pub/Sub Topic) Topic to be serialized.
  Returns:
    A serialized object representing a Cloud Pub/Sub Topic
    operation (create, delete).
  """
  topic_display_dict = resource_projector.MakeSerializable(topic)
  topic_display_dict['topicId'] = topic.name
  del topic_display_dict['name']

  return topic_display_dict


def SubscriptionDisplayDict(subscription):
  """Creates a serializable from a Cloud Pub/Sub Subscription op for display.

  Args:
    subscription: (Cloud Pub/Sub Subscription) Subscription to be serialized.
  Returns:
    A serialized object representing a Cloud Pub/Sub Subscription
    operation (create, delete, update).
  """
  push_endpoint = ''
  subscription_type = 'pull'
  if subscription.pushConfig:
    if subscription.pushConfig.pushEndpoint:
      push_endpoint = subscription.pushConfig.pushEndpoint
      subscription_type = 'push'

  return {
      'subscriptionId': subscription.name,
      'topic': subscription.topic,
      'type': subscription_type,
      'pushEndpoint': push_endpoint,
      'ackDeadlineSeconds': subscription.ackDeadlineSeconds,
      'retainAckedMessages': bool(subscription.retainAckedMessages),
      'messageRetentionDuration': subscription.messageRetentionDuration,
  }


def SnapshotDisplayDict(snapshot):
  """Creates a serializable from a Cloud Pub/Sub Snapshot operation for display.

  Args:
    snapshot: (Cloud Pub/Sub Snapshot) Snapshot to be serialized.

  Returns:
    A serialized object representing a Cloud Pub/Sub Snapshot operation (create,
    delete).
  """
  return {
      'snapshotId': snapshot.name,
      'topic': snapshot.topic,
      'expireTime': snapshot.expireTime,
  }
