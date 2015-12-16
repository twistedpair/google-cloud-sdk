# Copyright 2014 Google Inc. All Rights Reserved.

"""A library that is used to support logging commands."""

import json

from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log as sdk_log
from googlecloudsdk.third_party.apitools.base.py import extra_types


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


def ConvertToJsonObject(json_string):
  """Try to convert the JSON string into JsonObject."""
  try:
    return extra_types.JsonProtoDecoder(json_string)
  except Exception as e:
    raise exceptions.ToolException('Invalid JSON value: %s' % e.message)


def ExtractLogName(full_name):
  """Extract only the log name and restore original slashes.

  Args:
    full_name: The full log uri e.g projects/my-projects/logs/my-log.

  Returns:
    A log name that can be used in other commands.
  """
  log_name = full_name.split('/logs/', 1)[1]
  return log_name.replace('%2F', '/')


def PrintPermissionInstructions(destination):
  """Print a message to remind the user to set up permissions for a sink.

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
