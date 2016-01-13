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
import json
import re

from googlecloudsdk.calliope import exceptions as sdk_ex
from googlecloudsdk.core import properties
from googlecloudsdk.third_party.apitools.base.py import exceptions as api_ex

# Maximum number of results that can be passed in pageSize to list operations.
MAX_LIST_RESULTS = 10000

# Regular expression to match full paths for Cloud Pub/Sub resource identifiers.
PROJECT_PATH_RE = re.compile(r'^projects/(?P<Project>[^/]+)$')
SUBSCRIPTIONS_PATH_RE = re.compile(
    r'^projects/(?P<Project>[^/]+)/subscriptions/(?P<Resource>[^/]+)$')
TOPICS_PATH_RE = re.compile(
    r'^projects/(?P<Project>[^/]+)/topics/(?P<Resource>[^/]+)$')


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
    resource identifier type (subscriptions, topics).
    """
    pass

  def __init__(self, *args, **kwargs):
    self.Parse(*args, **kwargs)

  def Parse(self, resource_path, project_path=''):
    """Initializes a new ResourceIdentifier.

    Args:
      resource_path: (string) Full (ie. projects/my-proj/topics/my-topic)
                     or partial (my-topic) resource path.
      project_path: (string) Full (projects/my-project) or
                    partial (my-project) project path.
                    If empty, the SDK environment default
                    (gcloud config set project) will be used.
    Returns:
      An instantiated ResourceIdentifier with correct resource information
      (project path, full path).

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


def TopicMatches(topic_path, name_rgx):
  """Matches a full topic path against a regular expression for a topic name.

  Args:
    topic_path: (string) Full topic path
                       (ie. projects/my-project/topics/my-topic) to match.
    name_rgx: (string) Topic name regular expression to match against
              the topic_path.

  Returns:
    A re.match object if the regular expression matches
    the topic_path or None otherwise.

  Raises:
    sdk_ex.HttpException On an invalid regular expression syntax.
  """
  if '/' in name_rgx:
    raise sdk_ex.HttpException('Invalid --name-filter. Must not contain "/".')
  return re.match(TopicIdentifier(name_rgx).GetFullPath(), topic_path)


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


def SubscriptionMatches(subscription_path, name_rgx):
  """Matches a full subscription path against a regex for a subscription name.

  Args:
    subscription_path: (string) Full subscription path
                       (ie. projects/my-project/subscriptions/my-subscription)
                       to match.
    name_rgx: (string) Subscription name regular expression to match against
              the subscription_path.

  Returns:
    A re.match object if the regular expression matches the subscription_path
    or None otherwise.

  Raises:
    sdk_ex.HttpException On an invalid regular expression syntax.
  """
  if '/' in name_rgx:
    raise sdk_ex.HttpException('Invalid --name-filter. Must not contain "/".')

  return re.match(SubscriptionIdentifier(name_rgx).GetFullPath(),
                  subscription_path)


def MapHttpError(f):
  def Func(*args, **kwargs):
    try:
      return f(*args, **kwargs)
    except api_ex.HttpError as e:
      raise sdk_ex.HttpException(json.loads(e.content)['error']['message'])
  return Func
