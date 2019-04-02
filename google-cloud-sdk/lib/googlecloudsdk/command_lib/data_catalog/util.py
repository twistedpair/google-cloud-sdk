# -*- coding: utf-8 -*- #
# Copyright 2019 Google Inc. All Rights Reserved.
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
"""Utilities for Cloud Data Catalog commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.protorpclite import messages as _messages
from apitools.base.py import encoding
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import yaml


DATACATALOG_DEFAULT_API_VERSION = 'v1beta1'


class InvalidSchemaError(exceptions.Error):
  """Error if a schema is improperly specified."""


class InvalidSchemaFileError(exceptions.Error):
  """Error if a schema file is not valid JSON or YAML."""


def GetMessagesModule(api_version=DATACATALOG_DEFAULT_API_VERSION):
  return apis.GetMessagesModule('datacatalog', api_version)


def GetClientInstance(api_version=DATACATALOG_DEFAULT_API_VERSION):
  return apis.GetClientInstance('datacatalog', api_version)


def CorrectUpdateMask(ref, args, request):
  """Returns the update request with the corrected mask.

  The API expects a request with an update mask of 'schema', whereas the inline
  schema argument generates an update mask of 'schema.columns'. So if --schema
  was specified, we have to correct the update mask.

  Args:
    ref: The entry resource reference.
    args: The parsed args namespace.
    request: The update entry request.
  Returns:
    Request with corrected update mask.
  """
  del ref
  if args.IsSpecified('schema'):
    request.updateMask = request.updateMask.replace('schema.columns', 'schema')
  return request


def ProcessSchemaFromFile(schema_file):
  try:
    schema = yaml.load(schema_file)
  except yaml.YAMLParseError as e:
    raise InvalidSchemaFileError(
        'Error parsing schema file: [{}]'.format(e))
  return _SchemaToMessage(schema)


# TODO(b/127861769): Improve schema validation.
def _SchemaToMessage(schema):
  """Converts the given schema dict to the corresponding schema message.

  Args:
    schema: dict, The schema that has been processed.
  Returns:
    googleCloudDatacatalogV1betaSchema
  Raises:
    InvalidSchemaError: If the schema is invalid.
  """
  messages = GetMessagesModule()

  try:
    schema_message = encoding.DictToMessage(
        {'columns': schema},
        messages.GoogleCloudDatacatalogV1beta1Schema)
  except AttributeError:
    # TODO(b/77547931): Fix apitools bug related to unchecked iteritems() call.
    raise InvalidSchemaError(
        'Invalid schema: expected list of column names along with their types, '
        'modes, descriptions, and/or nested subcolumns.')
  except _messages.ValidationError as e:
    # Unfortunately apitools doesn't provide a way to get the path to the
    # invalid field here.
    raise InvalidSchemaError('Invalid schema: [{}]'.format(e))
  unrecognized_field_paths = _GetUnrecognizedFieldPaths(schema_message)
  if unrecognized_field_paths:
    error_msg_lines = ['Invalid schema, the following fields are unrecognized:']
    error_msg_lines += unrecognized_field_paths
    raise InvalidSchemaError('\n'.join(error_msg_lines))

  return schema_message


def _GetUnrecognizedFieldPaths(message):
  """Returns the field paths for unrecognized fields in the message."""
  errors = encoding.UnrecognizedFieldIter(message)
  unrecognized_field_paths = []
  for edges_to_message, field_names in errors:
    message_field_path = '.'.join(str(e) for e in edges_to_message)
    # Don't print the top level columns field since the user didn't specify it
    message_field_path = message_field_path.replace('columns', '', 1)
    for field_name in field_names:
      unrecognized_field_paths.append('{}.{}'.format(
          message_field_path, field_name))
  return sorted(unrecognized_field_paths)
