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

"""Facilities for constructing messages for schemas specified in flags."""

import json
import os

from googlecloudsdk.api_lib.bigquery import bigquery


def ReadSchema(schema, bigquery_messages):
  """Create a schema from a comma-separated list of field specifications.

  Each field specification is of the form name[:type], where an absent type
  specifies 'STRING'.

  Args:
    schema: A filename or schema.
    bigquery_messages: The messages module for the Bigquery API.

  Returns:
    The new schema, as a TableSchema message.

  Raises:
    bigquery.SchemaError: If the schema is invalid or the filename does
        not exist.
  """

  return bigquery_messages.TableSchema(
      fields=[
          _TableFieldSchemaForEntry(entry, bigquery_messages)
          for entry in schema.split(',')])


def _TableFieldSchemaForEntry(entry, bigquery_messages):
  field_name, _, field_type = entry.partition(':')
  if entry.count(':') > 1 or not field_name.strip():
    raise bigquery.SchemaError(
        'Invalid schema entry: {0}'.format(entry))
  return bigquery_messages.TableFieldSchema(
      name=field_name.strip(), type=field_type.strip().upper() or 'STRING')


def ReadSchemaFile(schema_file, bigquery_messages):
  """Create a schema message from the name of a file containing a JSON schema.

  Args:
    schema_file: A filename.
    bigquery_messages: The messages module for the Bigquery API.

  Returns:
    The new schema, as a TableSchema message.

  Raises:
    bigquery.SchemaError: If the schema is invalid or the filename does
        not exist.
  """

  if os.path.exists(schema_file):
    with open(schema_file, mode='r') as f:
      try:
        def UpperOrNone(string):
          return string and string.upper()
        field_schemas = [
            bigquery_messages.TableFieldSchema(
                name=json_object.get('name'),
                type=json_object.get('type').upper(),
                mode=UpperOrNone(json_object.get('mode')))
            for json_object in json.load(f)]
        return bigquery_messages.TableSchema(fields=field_schemas)
      except ValueError as e:
        raise bigquery.SchemaError(
            'Error decoding JSON schema from file {0}: {1}.'.format(
                schema_file, e))
  else:
    raise bigquery.SchemaError(
        'Error reading schema: File "{0}" was not found.'.format(schema_file))
