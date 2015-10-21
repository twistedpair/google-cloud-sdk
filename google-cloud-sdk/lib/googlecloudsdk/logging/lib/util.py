# Copyright 2014 Google Inc. All Rights Reserved.

"""A library that is used to support logging commands."""

import json

from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log as sdk_log
from googlecloudsdk.third_party.apitools.base.py import extra_types


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
