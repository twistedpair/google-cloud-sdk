# Copyright 2015 Google Inc. All Rights Reserved.
"""A library that is used to support Cloud Pub/Sub commands."""

import json
import re

from googlecloudsdk.calliope import exceptions as sdk_ex
from googlecloudsdk.core import properties
from googlecloudsdk.third_party.apitools.base.py import exceptions as api_ex


def RaiseErrorIfArgIsAPath(f):
  """Verifies that the first argument to the function, is not a path."""

  def Func(*args, **kwargs):
    if args and args[0].startswith('projects/'):
      raise sdk_ex.HttpException('Topics and/or subscription names'
                                 ' should not start with the prefix'
                                 ' "projects/"')
    return f(*args, **kwargs)
  return Func


@RaiseErrorIfArgIsAPath
def _ProjectFormat(project_name):
  return 'projects/{0}'.format(project_name)


def ProjectFormat(project_name=''):
  if not project_name:
    project_name = properties.VALUES.core.project.Get(required=True)
  return _ProjectFormat(project_name)


@RaiseErrorIfArgIsAPath
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
  return '{0}/topics/{1}'.format(ProjectFormat(topic_project), topic_name)


def TopicMatches(topic_path, name_rgx):
  """Matches a topic path against a regular expression for a topic name.

  Args:
    topic_path: (string) Topic path to match.
    name_rgx: (string) Topic name regular expression to match against
              the topic_path.

  Returns:
    A re.match object if the regular expression matches
    the topic_path or None otherwise.
  """
  return re.match(
      '{0}/topics/{1}'.format(ProjectFormat(), name_rgx), topic_path)


@RaiseErrorIfArgIsAPath
def SubscriptionFormat(subscription_name):
  """Formats a subscription name as a fully qualified subscription path.

  Args:
    subscription_name: (string) Name of the subscription to convert.

  Returns:
    Returns a fully qualified subscription path of the
    form project/foo/subscriptions/subscription_name.
  """
  return '{0}/subscriptions/{1}'.format(ProjectFormat(), subscription_name)


def SubscriptionMatches(subscription_path, name_rgx):
  """Matches a subscription path against a regex for a subscription name.

  Args:
    subscription_path: (string) Subscription path to match.
    name_rgx: (string) Subscription name regular expression to match against
              the subscription_path.

  Returns:
    A re.match object if the regular expression matches the subscription_path
    or None otherwise.
  """
  return re.match(
      '{0}/subscriptions/{1}'.format(ProjectFormat(), name_rgx),
      subscription_path)


def MapHttpError(f):
  def Func(*args, **kwargs):
    try:
      return f(*args, **kwargs)
    except api_ex.HttpError as e:
      raise sdk_ex.HttpException(json.loads(e.content)['error']['message'])
  return Func
