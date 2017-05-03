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

"""A library that is used to support Functions commands."""

import functools
import json
import os
import re
import sys

from apitools.base.py import exceptions as apitools_exceptions

import enum
from googlecloudsdk.api_lib.functions import exceptions
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import exceptions as base_exceptions
from googlecloudsdk.core.util import encoding

_ENTRY_POINT_NAME_RE = re.compile(
    r'^(?=.{1,128}$)[_a-zA-Z0-9]+(?:\.[_a-zA-Z0-9]+)*$')
_ENTRY_POINT_NAME_ERROR = (
    'Entry point name must contain only Latin letters (lower- or '
    'upper-case), digits, dot (.) and underscore (_), and must be at most 128 '
    'characters long. It can neither begin nor end with a dot (.), '
    'nor contain two consecutive dots (..).')

_FUNCTION_NAME_RE = re.compile(r'^[A-Za-z](?:[-_A-Za-z0-9]{0,46}[A-Za-z0-9])?$')
_FUNCTION_NAME_ERROR = (
    'Function name must contain only lower case Latin letters, digits and a '
    'hyphen (-). It must start with letter, must not end with a hyphen, '
    'and must be at most 63 characters long.')

_TOPIC_NAME_RE = re.compile(r'^[a-zA-Z][\-\._~%\+a-zA-Z0-9]{2,254}$')
_TOPIC_NAME_ERROR = (
    'Topic must contain only Latin letters (lower- or upper-case), digits and '
    'the characters - + . _ ~ %. It must start with a letter and be from 3 to '
    '255 characters long.')

_BUCKET_URI_RE = re.compile(
    r'^(?:gs://)?[a-z\d][a-z\d\._-]{1,230}[a-z\d]/?$')
_BUCKET_URI_ERROR = (
    'Bucket must only contain lower case Latin letters, digits and '
    'characters . _ -. It must start and end with a letter or digit '
    'and be from 3 to 232 characters long. You may optionally prepend the '
    'bucket name with gs:// and append / at the end.')

_API_NAME = 'cloudfunctions'
_API_VERSION = 'v1beta2'


def GetApiClientInstance():
  return apis.GetClientInstance(_API_NAME, _API_VERSION)


def GetApiMessagesModule():
  return apis.GetMessagesModule(_API_NAME, _API_VERSION)


@enum.unique
class Resources(enum.Enum):

  class Resource(object):

    def __init__(self, name, collection_id):
      self.name = name
      self.collection_id = collection_id
  TOPIC = Resource('topic', 'pubsub.projects.topics')
  BUCKET = Resource('bucket', 'cloudfunctions.projects.buckets')
  PROJECT = Resource('project', 'cloudresourcemanager.projects')


class TriggerProvider(object):
  """Represents --trigger-provider flag value options."""

  def __init__(self, label, events):
    self.label = label
    self.events = events
    for event in self.events:
      event.provider = self

  @property
  def default_event(self):
    return self.events[0]


class TriggerEvent(object):
  """Represents --trigger-event flag value options."""

  # Currently any and only project resource is optional
  optional_resource_types = [Resources.PROJECT]

  def __init__(self, label, resource_type):
    self.label = label
    self.resource_type = resource_type

  @property
  def event_is_optional(self):
    return self.provider.default_event == self

  # TODO(b/33097692) Let TriggerEvent know how to handle optional resources.
  @property
  def resource_is_optional(self):
    return self.resource_type in TriggerEvent.optional_resource_types

# Don't use those structures directly. Use registry object instead.
# By convention, first event type is default.
_BETA_PROVIDERS = [
    TriggerProvider('cloud.pubsub', [
        TriggerEvent('topic.publish', Resources.TOPIC),
    ]),
    TriggerProvider('cloud.storage', [
        TriggerEvent('object.change', Resources.BUCKET),
    ]),
]

_ALPHA_PROVIDERS = [
    TriggerProvider('firebase.auth', [
        TriggerEvent('user.create', Resources.PROJECT),
        TriggerEvent('user.delete', Resources.PROJECT),
    ]),
    TriggerProvider('firebase.database', [
        TriggerEvent('data.write', Resources.PROJECT),
    ])
]


class _TriggerProviderRegistry(object):
  """This class encapsulates all Event Trigger related functionality."""

  def __init__(self, all_providers):
    self.providers = all_providers

  def ProvidersLabels(self):
    return (p.label for p in self.providers)

  def Provider(self, provider):
    return next((p for p in self.providers if p.label == provider))

  def EventsLabels(self, provider):
    return (e.label for e in self.Provider(provider).events)

  def Event(self, provider, event):
    return next((e for e in self.Provider(provider).events if e.label == event))


output_trigger_provider_registry = _TriggerProviderRegistry(_BETA_PROVIDERS)
input_trigger_provider_registry = _TriggerProviderRegistry(
    _BETA_PROVIDERS + _ALPHA_PROVIDERS)


_ID_CHAR = '[a-zA-Z0-9_]'
_P_CHAR = "[][~@#$%&.,?:;+*='()-]"
# capture: '{' ID_CHAR+ ('=' '*''*'?)? '}'
# Named wildcards may be written in curly brackets (e.g. {variable}). The
# value that matched this parameter will be included  in the event
# parameters.
_CAPTURE = r'(\{' + _ID_CHAR + r'(=\*\*?)?})'
# segment: (ID_CHAR | P_CHAR)+
_SEGMENT = '((' + _ID_CHAR + '|' + _P_CHAR + ')+)'
# part: '/' segment | capture
_PART = '(/(' + _SEGMENT + '|' + _CAPTURE + '))'
# path: part+ (but first / is optional)
_PATH = '(/?(' + _SEGMENT + '|' + _CAPTURE + ')' + _PART + '*)'

_PATH_RE_ERROR = ('Path must be a slash-separated list of segments and '
                  'captures. For example, [users/{userId}/profilePic].')


def GetHttpErrorMessage(error):
  """Returns a human readable string representation from the http response.

  Args:
    error: HttpException representing the error response.

  Returns:
    A human readable string representation of the error.
  """
  status = error.response.status
  code = error.response.reason
  message = ''
  try:
    data = json.loads(error.content)
    if 'error' in data:
      error_info = data['error']
      if 'message' in error_info:
        message = error_info['message']
      violations = _GetViolationsFromError(error_info)
      if violations:
        message += '\nProblems:\n' + violations
  except (ValueError, TypeError):
    message = error.content
  return u'ResponseError: status=[{0}], code=[{1}], message=[{2}]'.format(
      status, code, encoding.Decode(message))


def GetOperationError(error):
  """Returns a human readable string representation from the operation.

  Args:
    error: A string representing the raw json of the operation error.

  Returns:
    A human readable string representation of the error.
  """
  return u'OperationError: code={0}, message={1}'.format(
      error.code, encoding.Decode(error.message))


def _ValidateArgumentByRegexOrRaise(argument, regex, error_message):
  if isinstance(regex, str):
    match = re.match(regex, argument)
  else:
    match = regex.match(argument)
  if not match:
    raise arg_parsers.ArgumentTypeError(
        "Invalid value '{0}': {1}".format(argument, error_message))
  return argument


def ValidateFunctionNameOrRaise(name):
  """Checks if a function name provided by user is valid.

  Args:
    name: Function name provided by user.
  Returns:
    Function name.
  Raises:
    ArgumentTypeError: If the name provided by user is not valid.
  """
  return _ValidateArgumentByRegexOrRaise(name, _FUNCTION_NAME_RE,
                                         _FUNCTION_NAME_ERROR)


def ValidateEntryPointNameOrRaise(entry_point):
  """Checks if a entry point name provided by user is valid.

  Args:
    entry_point: Entry point name provided by user.
  Returns:
    Entry point name.
  Raises:
    ArgumentTypeError: If the entry point name provided by user is not valid.
  """
  return _ValidateArgumentByRegexOrRaise(entry_point, _ENTRY_POINT_NAME_RE,
                                         _ENTRY_POINT_NAME_ERROR)


def ValidateAndStandarizeBucketUriOrRaise(bucket):
  """Checks if a bucket uri provided by user is valid.

  If the Bucket uri is valid, converts it to a standard form.

  Args:
    bucket: Bucket uri provided by user.
  Returns:
    Sanitized bucket uri.
  Raises:
    ArgumentTypeError: If the name provided by user is not valid.
  """
  bucket = _ValidateArgumentByRegexOrRaise(bucket, _BUCKET_URI_RE,
                                           _BUCKET_URI_ERROR)
  if not bucket.endswith('/'):
    bucket += '/'
  if not bucket.startswith('gs://'):
    bucket = 'gs://' + bucket
  return bucket


def ValidatePubsubTopicNameOrRaise(topic):
  """Checks if a Pub/Sub topic name provided by user is valid.

  Args:
    topic: Pub/Sub topic name provided by user.
  Returns:
    Topic name.
  Raises:
    ArgumentTypeError: If the name provided by user is not valid.
  """
  topic = _ValidateArgumentByRegexOrRaise(topic, _TOPIC_NAME_RE,
                                          _TOPIC_NAME_ERROR)
  return topic


def ValidateDirectoryExistsOrRaiseFunctionError(directory):
  """Checks if a source directory exists.

  Args:
    directory: A string: a local path to directory provided by user.
  Returns:
    The argument provided, if found valid.
  Raises:
    ArgumentTypeError: If the user provided a directory which is not valid.
  """
  if not os.path.exists(directory):
    raise exceptions.FunctionsError(
        'argument --source: Provided directory does not exist. If '
        'you intended to provide a path to Google Cloud Repository, you must '
        'specify the --source-url argument')
  if not os.path.isdir(directory):
    raise exceptions.FunctionsError(
        'argument --source: Provided path does not point to a directory. If '
        'you intended to provide a path to Google Cloud Repository, you must '
        'specify the --source-url argument')
  return directory


def ValidatePathOrRaise(path):
  """Check if path provided by user is valid.

  Args:
    path: A string: resource path
  Returns:
    The argument provided, if found valid.
  Raises:
    ArgumentTypeError: If the user provided a path which is not valid
  """
  path = _ValidateArgumentByRegexOrRaise(path, _PATH, _PATH_RE_ERROR)
  return path


def _GetViolationsFromError(error_info):
  """Looks for violations descriptions in error message.

  Args:
    error_info: json containing error information.
  Returns:
    List of violations descriptions.
  """
  result = ''
  details = None
  try:
    if 'details' in error_info:
      details = error_info['details']
    for field in details:
      if 'fieldViolations' in field:
        violations = field['fieldViolations']
        for violation in violations:
          if 'description' in violation:
            result += violation['description'] + '\n'
  except (ValueError, TypeError):
    pass
  return result


def CatchHTTPErrorRaiseHTTPException(func):
  # TODO(b/36052526): merge this function with HandleHttpError defined
  # elsewhere:
  # * shared/projects/util.py
  # * shared/dns/util.py
  # (obstacle: GetHttpErrorMessage function may be project-specific)
  """Decorator that catches HttpError and raises corresponding exception."""

  @functools.wraps(func)
  def CatchHTTPErrorRaiseHTTPExceptionFn(*args, **kwargs):
    try:
      return func(*args, **kwargs)
    except apitools_exceptions.HttpError as error:
      msg = GetHttpErrorMessage(error)
      unused_type, unused_value, traceback = sys.exc_info()
      raise base_exceptions.HttpException, msg, traceback

  return CatchHTTPErrorRaiseHTTPExceptionFn


def FormatTimestamp(timestamp):
  """Formats a timestamp which will be presented to a user.

  Args:
    timestamp: Raw timestamp string in RFC3339 UTC "Zulu" format.
  Returns:
    Formatted timestamp string.
  """
  return re.sub(r'(\.\d{3})\d*Z$', r'\1', timestamp.replace('T', ' '))
