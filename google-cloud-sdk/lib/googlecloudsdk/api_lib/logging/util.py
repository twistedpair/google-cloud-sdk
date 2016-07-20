# Copyright 2014 Google Inc. All Rights Reserved.
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

"""A library that is used to support logging commands."""

import functools
import json

from apitools.base.py import exceptions as apitools_exceptions
from apitools.base.py import extra_types

from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log as sdk_log


class TypedLogSink(object):
  """Class that encapsulates V1 and V2 LogSinks during the transition period.

  Attributes:
    name: present in both versions.
    destination: present in both versions.
    filter: present in both versions.
    format: format of exported entries, only present in V2 sinks.
    type: one-of log/service/project.
  """

  def __init__(self, sink, log_name=None, service_name=None):
    """Creates a TypedLogSink with type based on constructor values.

    Args:
      sink: instance of V1 or V2 LogSink
      log_name: name of log, if it's a log-sink.
      service_name: name of service, if it's a service-sink
    """
    self.name = sink.name
    self.destination = sink.destination
    self.filter = None
    # Get sink type.
    if log_name:
      self.type = 'LOG: %s' % log_name
    elif service_name:
      self.type = 'SERVICE: %s' % service_name
    else:
      self.type = 'PROJECT SINK'
      self.filter = sink.filter if sink.filter else '(empty filter)'
    # Get sink format.
    if hasattr(sink, 'outputVersionFormat'):
      self.format = sink.outputVersionFormat.name
    else:
      self.format = 'V1'


def CheckSinksCommandArguments(args):
  """Validates arguments that are provided to 'sinks create/update' command.

  Args:
    args: arguments returned from argparser.

  Raises:
    InvalidArgumentException on error.
  """
  is_project_sink = not (args.log or args.service)

  if not is_project_sink and args.log_filter:
    raise exceptions.InvalidArgumentException(
        '--log-filter', 'Only project sinks support filters')

  if not is_project_sink and args.output_version_format == 'V2':
    raise exceptions.InvalidArgumentException(
        '--output-version-format', 'Only project sinks support V2 format')


def FormatTimestamp(timestamp):
  """Returns a string representing timestamp in RFC3339 format.

  Args:
    timestamp: A datetime.datetime object.

  Returns:
    A timestamp string in format, which is accepted by Cloud Logging.
  """
  return timestamp.strftime('%Y-%m-%dT%H:%M:%S.%fZ')


def GetError(error):
  """Returns a ready-to-print string representation from the http response.

  Args:
    error: A string representing the raw json of the Http error response.

  Returns:
    A ready-to-print string representation of the error.
  """
  status = error.response.status
  code = error.response.reason
  try:
    data = json.loads(error.content)
    message = data['error']['message']
  except ValueError:
    message = error.content
  return ('ResponseError: status=%s, code=%s, message=%s'
          % (status, code, message))


# TODO(user): Switch to using gcloud provided methods when they are ready.
def HandleHttpError(func):
  """Decorator that handles http errors from methods."""

  @functools.wraps(func)
  def CatchHTTPErrorRaiseHTTPException(*args, **kwargs):
    try:
      return func(*args, **kwargs)
    except apitools_exceptions.HttpError as error:
      raise exceptions.HttpException(GetError(error))

  return CatchHTTPErrorRaiseHTTPException


def HandlePagerHttpError(func):
  """Decorator that handles http errors, for methods that return a generator."""

  @functools.wraps(func)
  def CatchHTTPErrorRaiseHTTPException(*args, **kwargs):
    try:
      for result in func(*args, **kwargs):
        yield result
    except apitools_exceptions.HttpError as error:
      raise exceptions.HttpException(GetError(error))

  return CatchHTTPErrorRaiseHTTPException


def ConvertToJsonObject(json_string):
  """Tries to convert the JSON string into JsonObject."""
  try:
    return extra_types.JsonProtoDecoder(json_string)
  except Exception as e:
    raise exceptions.ToolException('Invalid JSON value: %s' % e.message)


def CreateLogResourceName(parent, log_id):
  """Creates the full log resource name.

  Args:
    parent: The project or organization id as a resource name, e.g.
      'projects/my-project' or 'organizations/123'.
    log_id: The log id, e.g. 'my-log'. This may already be a resource name, in
      which case parent is ignored and log_id is returned directly, e.g.
      CreateLogResourceName('projects/ignored', 'projects/bar/logs/my-log')
      returns 'projects/bar/logs/my-log'

  Returns:
    Log resource, e.g. projects/my-project/logs/my-log.
  """
  if '/logs/' in log_id:
    return log_id
  return '%s/logs/%s' % (parent, log_id.replace('/', '%2F'))


def ExtractLogId(log_resource):
  """Extracts only the log id and restore original slashes.

  Args:
    log_resource: The full log uri e.g projects/my-projects/logs/my-log.

  Returns:
    A log id that can be used in other commands.
  """
  log_id = log_resource.split('/logs/', 1)[1]
  return log_id.replace('%2F', '/')


def PrintPermissionInstructions(destination):
  """Prints a message to remind the user to set up permissions for a sink.

  Args:
    destination: the sink destination (either bigquery or cloud storage).
  """
  if destination.startswith('bigquery'):
    sdk_log.Print('Please remember to grant the group `cloud-logs@google.com` '
                  'the WRITER role on the dataset.')
  elif destination.startswith('storage'):
    sdk_log.Print('Please remember to grant the group `cloud-logs@google.com` '
                  'full-control access to the bucket.')
  elif destination.startswith('pubsub'):
    sdk_log.Print('Please remember to grant the group `cloud-logs@google.com` '
                  'EDIT permission to the project.')
  sdk_log.Print('More information about sinks can be found at '
                'https://cloud.google.com/logging/docs/export/configure_export')
