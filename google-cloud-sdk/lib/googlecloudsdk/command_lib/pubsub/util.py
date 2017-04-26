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

import abc
import re

from googlecloudsdk.api_lib.util import exceptions as sdk_ex
from googlecloudsdk.core import properties
from googlecloudsdk.core.resource import resource_projector

# Maximum number of results that can be passed in pageSize to list operations.
MAX_LIST_RESULTS = 10000

# Regular expression to match full paths for Cloud Pub/Sub resource identifiers.
# TODO(b/36211390): These are going away, since we are moving to
# collection paths in CL/125390647.
PROJECT_PATH_RE = re.compile(r'^projects/(?P<Project>[^/]+)$')
SNAPSHOTS_PATH_RE = re.compile(
    r'^projects/(?P<Project>[^/]+)/snapshots/(?P<Resource>[^/]+)$')
SUBSCRIPTIONS_PATH_RE = re.compile(
    r'^projects/(?P<Project>[^/]+)/subscriptions/(?P<Resource>[^/]+)$')
TOPICS_PATH_RE = re.compile(
    r'^projects/(?P<Project>[^/]+)/topics/(?P<Resource>[^/]+)$')

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


# TODO(b/32275946): Use core.resources.Resource instead of this custom class.
class ResourceIdentifier(object):
  """Base class to build resource identifiers."""
  __metaclass__ = abc.ABCMeta

  @abc.abstractmethod
  def _RegexMatch(self, resource_path):
    """Return a match object from applying a regexp to this resource identifier.

    This function needs to be overriden in subclasses to use the appropriate
    regular expression for a resource identifier type (subscriptions, topics).

    Args:
      resource_path: (string) Full (ie. projects/my-proj/topics/my-topic)
                     or partial (my-topic) project or resource path.
    """
    pass

  @abc.abstractmethod
  def _ResourceType(self):
    """Returns the valid resource identifier type for this instance.

    This function needs to be overriden in subclasses to return a valid
    resource identifier type (subscriptions, topics, or snapshots).
    """
    pass

  def __init__(self, *args, **kwargs):
    self.Parse(*args, **kwargs)

  def Parse(self, resource_path, project_path=''):
    """Initializes a new ResourceIdentifier.

    Args:
      resource_path: (string) Full (e.g., projects/my-proj/topics/my-topic)
                     or partial (my-topic) resource path.
      project_path: (string) Full (projects/my-project) or
                    partial (my-project) project path.
                    If empty, the SDK environment default
                    (gcloud config set project) will be used.
    Returns:
      A ResourceIdentifier instance that captures the subcomponents of the
      resource identifier.

    Raises:
      HttpException if the provided resource path is not a valid resource
      path/name.
    """
    if '/' in resource_path:
      match = self._RegexMatch(resource_path)
      if match is None:
        raise sdk_ex.HttpException(
            'Invalid {0} Identifier'.format(self._ResourceType().capitalize()))

      self.project = ProjectIdentifier(match.groupdict()['Project'])
      self.resource_name = match.groupdict()['Resource']
      return

    self.project = ProjectIdentifier(project_path)
    self.resource_name = resource_path

  def GetFullPath(self):
    return '{0}/{1}/{2}'.format(self.project.GetFullPath(),
                                self._ResourceType(),
                                self.resource_name)


class ProjectIdentifier(ResourceIdentifier):
  """Represents a Cloud project identifier."""

  def Parse(self, project_path=''):
    """Initializes a new ProjectIdentifier.

    Args:
      project_path: (string) Full (projects/my-proj) or partial (my-proj)
                    project path.
                    If empty, the SDK environment default
                    (gcloud config set project) will be used.
    Returns:
      An instantiated ProjectIdentifier with correct project information.

    Raises:
      HttpException if the provided project path is not a valid project
      path/name or if a default project have not been set.
    """
    if not project_path:
      self.project_name = properties.VALUES.core.project.Get(required=True)
      return

    if '/' in project_path:
      match = self._RegexMatch(project_path)
      if match is None:
        raise sdk_ex.HttpException('Invalid Project Identifier')

      self.project_name = match.groupdict()['Project']
      return

    self.project_name = project_path

  def _ResourceType(self):
    return 'projects'

  def _RegexMatch(self, resource_path):
    return PROJECT_PATH_RE.match(resource_path)

  def GetFullPath(self):
    """Returns a valid full project path."""
    return '{0}/{1}'.format(self._ResourceType(), self.project_name)


class SnapshotIdentifier(ResourceIdentifier):
  """Represents a Cloud Pub/Sub snapshot identifier."""

  def _RegexMatch(self, resource_path):
    return SNAPSHOTS_PATH_RE.match(resource_path)

  def _ResourceType(self):
    return 'snapshots'


class SubscriptionIdentifier(ResourceIdentifier):
  """Represents a Cloud Pub/Sub subscription identifier."""

  def _RegexMatch(self, resource_path):
    return SUBSCRIPTIONS_PATH_RE.match(resource_path)

  def _ResourceType(self):
    return 'subscriptions'


class TopicIdentifier(ResourceIdentifier):
  """Represents a Cloud Pub/Sub topic identifier."""

  def _RegexMatch(self, resource_path):
    return TOPICS_PATH_RE.match(resource_path)

  def _ResourceType(self):
    return 'topics'


def ProjectFormat(project_name=''):
  return ProjectIdentifier(project_name).GetFullPath()


def TopicFormat(topic_name, topic_project=''):
  """Formats a topic name as a fully qualified topic path.

  Args:
    topic_name: (string) Name of the topic to convert.
    topic_project: (string) Name of the project the given topic belongs to.
                   If not given, then the project defaults to the currently
                   selected cloud project.

  Returns:
    Returns a fully qualified topic path of the
    form project/foo/topics/topic_name.
  """
  return TopicIdentifier(topic_name, topic_project).GetFullPath()


def SubscriptionFormat(subscription_name, project_name=''):
  """Formats a subscription name as a fully qualified subscription path.

  Args:
    subscription_name: (string) Name of the subscription to convert.
    project_name: (string) Name of the project the given subscription belongs
                  to. If not given, then the project defaults to the currently
                  selected cloud project.

  Returns:
    Returns a fully qualified subscription path of the
    form project/foo/subscriptions/subscription_name.
  """
  return SubscriptionIdentifier(subscription_name, project_name).GetFullPath()


def SnapshotFormat(snapshot_name, project_name=''):
  """Formats a snapshot name as a fully qualified snapshot path.

  Args:
    snapshot_name: (string) Name of the snapshot to convert.
    project_name: (string) Name of the project the given snapshot belongs
                  to. If not given, then the project defaults to the currently
                  selected cloud project.

  Returns:
    Returns a fully qualified snapshot path of the form
    project/foo/snapshots/snapshot_name.
  """
  return SnapshotIdentifier(snapshot_name, project_name).GetFullPath()


# TODO(b/32276674): Remove the use of custom *DisplayDict's.
def TopicDisplayDict(topic, error_msg=''):
  """Creates a serializable from a Cloud Pub/Sub Topic operation for display.

  Args:
    topic: (Cloud Pub/Sub Topic) Topic to be serialized.
    error_msg: (string) An error message to be added to the serialized
               result, if any.
  Returns:
    A serialized object representing a Cloud Pub/Sub Topic
    operation (create, delete).
  """
  topic_display_dict = resource_projector.MakeSerializable(topic)
  topic_display_dict['topicId'] = topic.name
  topic_display_dict['success'] = not error_msg
  topic_display_dict['reason'] = error_msg or ''
  del topic_display_dict['name']

  return topic_display_dict


def SubscriptionDisplayDict(subscription, error_msg=''):
  """Creates a serializable from a Cloud Pub/Sub Subscription op for display.

  Args:
    subscription: (Cloud Pub/Sub Subscription) Subscription to be serialized.
    error_msg: (string) An error message to be added to the serialized
               result, if any.
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
      'success': not error_msg,
      'reason': error_msg or '',
  }


def SnapshotDisplayDict(snapshot, error_msg=''):
  """Creates a serializable from a Cloud Pub/Sub Snapshot operation for display.

  Args:
    snapshot: (Cloud Pub/Sub Snapshot) Snapshot to be serialized.
    error_msg: (string) An error message to be added to the serialized
               result, if any.
  Returns:
    A serialized object representing a Cloud Pub/Sub Snapshot operation (create,
    delete).
  """
  return {
      'snapshotId': snapshot.name,
      'topic': snapshot.topic,
      'expireTime': snapshot.expireTime,
      'success': not error_msg,
      'reason': error_msg or '',
  }
