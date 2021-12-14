# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Cloud Datastream API utilities."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import uuid

from googlecloudsdk.api_lib.datastream import exceptions as ds_exceptions
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base
from googlecloudsdk.core import resources
from googlecloudsdk.core import yaml
from googlecloudsdk.core.console import console_io
import six

_DEFAULT_API_VERSION = 'v1'

# TODO(b/207467120): remove translation after BETA deprecation.
_UPDATE_MASK_FIELD_TRANSLATION_V1ALPHA1_TO_V1 = {
    'allowlist': 'include_objects',
    'rejectlist': 'exclude_objects',
    'source_connection_profile_name': 'source_connection_profile',
    'destination_connection_profile_name': 'destination_connection_profile',
    'vpc_name': 'vpc',
}
RDBMS_FIELD_NAME_BY_RELEASE_TRACK = {
    'schema': {
        base.ReleaseTrack.BETA: 'schema_name',
        base.ReleaseTrack.GA: 'schema'
    },
    'database': {
        base.ReleaseTrack.BETA: 'database_name',
        base.ReleaseTrack.GA: 'database'
    },
    'table': {
        base.ReleaseTrack.BETA: 'table_name',
        base.ReleaseTrack.GA: 'table'
    },
    'column': {
        base.ReleaseTrack.BETA: 'column_name',
        base.ReleaseTrack.GA: 'column'
    },
    'allowlist': {
        base.ReleaseTrack.BETA: 'allowlist',
        base.ReleaseTrack.GA: 'include_objects'
    },
    'rejectlist': {
        base.ReleaseTrack.BETA: 'rejectlist',
        base.ReleaseTrack.GA: 'exclude_objects'
    }
}


def GetClientInstance(api_version=_DEFAULT_API_VERSION, no_http=False):
  return apis.GetClientInstance('datastream', api_version, no_http=no_http)


def GetMessagesModule(api_version=_DEFAULT_API_VERSION):
  return apis.GetMessagesModule('datastream', api_version)


def GetResourceParser(api_version=_DEFAULT_API_VERSION):
  resource_parser = resources.Registry()
  resource_parser.RegisterApiByName('datastream', api_version)
  return resource_parser


def ParentRef(project, location):
  """Get the resource name of the parent collection.

  Args:
    project: the project of the parent collection.
    location: the GCP region of the membership.

  Returns:
    the resource name of the parent collection in the format of
    `projects/{project}/locations/{location}`.
  """

  return 'projects/{}/locations/{}'.format(project, location)


def GenerateRequestId():
  """Generates a UUID to use as the request ID.

  Returns:
    string, the 40-character UUID for the request ID.
  """
  return six.text_type(uuid.uuid4())


def ParseMysqlColumn(messages, mysql_column_object, release_track):
  """Parses a raw mysql column json/yaml into the MysqlColumn message."""
  return messages.MysqlColumn(
      column=mysql_column_object.get(
          _GetRDBMSFieldName('column_name', release_track), {}),
      dataType=mysql_column_object.get('data_type', {}),
      collation=mysql_column_object.get('collation', {}),
      length=mysql_column_object.get('length', {}),
      nullable=mysql_column_object.get('nullable', {}),
      ordinalPosition=mysql_column_object.get('ordinal_position', {}),
      primaryKey=mysql_column_object.get('primary_key', {}))


def ParseMysqlTable(messages, mysql_table_object, release_track):
  """Parses a raw mysql table json/yaml into the MysqlTable message."""
  mysql_column_msg_list = []
  for column in mysql_table_object.get('mysql_columns', []):
    mysql_column_msg_list.append(
        ParseMysqlColumn(messages, column, release_track))
  table_key = _GetRDBMSFieldName('table', release_track)
  table_name = mysql_table_object.get(table_key)
  if not table_name:
    raise ds_exceptions.ParseError('Cannot parse YAML: missing key "%s".' %
                                   table_key)
  return messages.MysqlTable(
      table=table_name, mysqlColumns=mysql_column_msg_list)


def ParseMysqlDatabase(messages, mysql_database_object, release_track):
  """Parses a raw mysql database json/yaml into the MysqlDatabase message."""
  mysql_tables_msg_list = []
  for table in mysql_database_object.get('mysql_tables', []):
    mysql_tables_msg_list.append(
        ParseMysqlTable(messages, table, release_track))
  database_key = _GetRDBMSFieldName('database', release_track)
  database_name = mysql_database_object.get(database_key)
  if not database_name:
    raise ds_exceptions.ParseError('Cannot parse YAML: missing key "%s".' %
                                   database_key)
  return messages.MysqlDatabase(
      database=database_name, mysqlTables=mysql_tables_msg_list)


def ParseMysqlRdbmsFile(messages,
                        mysql_rdbms_file,
                        release_track=base.ReleaseTrack.BETA):
  """Parses a mysql_rdbms_file into the MysqlRdbms message."""
  data = console_io.ReadFromFileOrStdin(mysql_rdbms_file, binary=False)
  try:
    mysql_rdbms_head_data = yaml.load(data)
  except Exception as e:
    raise ds_exceptions.ParseError('Cannot parse YAML:[{0}]'.format(e))

  mysql_rdbms_data = mysql_rdbms_head_data.get('mysql_rdbms',
                                               mysql_rdbms_head_data)
  return ParseMysqlSchemasListToMysqlRdbmsMessage(messages, mysql_rdbms_data,
                                                  release_track)


def ParseMysqlSchemasListToMysqlRdbmsMessage(messages,
                                             mysql_rdbms_data,
                                             release_track=base.ReleaseTrack
                                             .BETA):
  """Parses an object of type {mysql_databases: [...]} into the MysqlRdbms message."""
  mysql_databases_raw = mysql_rdbms_data.get('mysql_databases', [])
  mysql_database_msg_list = []
  for schema in mysql_databases_raw:
    mysql_database_msg_list.append(
        ParseMysqlDatabase(messages, schema, release_track))

  mysql_rdbms_msg = messages.MysqlRdbms(
      mysqlDatabases=mysql_database_msg_list)
  return mysql_rdbms_msg


def ParseOracleColumn(messages, oracle_column_object, release_track):
  """Parses a raw oracle column json/yaml into the OracleColumn message."""
  return messages.OracleColumn(
      column=oracle_column_object.get(
          _GetRDBMSFieldName('column', release_track), {}),
      dataType=oracle_column_object.get('data_type', {}),
      encoding=oracle_column_object.get('encoding', {}),
      length=oracle_column_object.get('length', {}),
      nullable=oracle_column_object.get('nullable', {}),
      ordinalPosition=oracle_column_object.get('ordinal_position', {}),
      precision=oracle_column_object.get('precision', {}),
      primaryKey=oracle_column_object.get('primary_key', {}),
      scale=oracle_column_object.get('scale', {}))


def ParseOracleTable(messages, oracle_table_object, release_track):
  """Parses a raw oracle table json/yaml into the OracleTable message."""
  oracle_columns_msg_list = []
  for column in oracle_table_object.get('oracle_columns', []):
    oracle_columns_msg_list.append(
        ParseOracleColumn(messages, column, release_track))
  table_key = _GetRDBMSFieldName('table', release_track)
  table_name = oracle_table_object.get(table_key)
  if not table_name:
    raise ds_exceptions.ParseError('Cannot parse YAML: missing key "%s".' %
                                   table_key)
  return messages.OracleTable(
      table=table_name, oracleColumns=oracle_columns_msg_list)


def ParseOracleSchema(messages, oracle_schema_object, release_track):
  """Parses a raw oracle schema json/yaml into the OracleSchema message."""
  oracle_tables_msg_list = []
  for table in oracle_schema_object.get('oracle_tables', []):
    oracle_tables_msg_list.append(
        ParseOracleTable(messages, table, release_track))
  schema_key = _GetRDBMSFieldName('schema', release_track)
  schema_name = oracle_schema_object.get(schema_key)
  if not schema_name:
    raise ds_exceptions.ParseError('Cannot parse YAML: missing key "%s".' %
                                   schema_key)
  return messages.OracleSchema(
      schema=schema_name, oracleTables=oracle_tables_msg_list)


def ParseOracleRdbmsFile(messages,
                         oracle_rdbms_file,
                         release_track=base.ReleaseTrack.BETA):
  """Parses a oracle_rdbms_file into the OracleRdbms message."""
  data = console_io.ReadFromFileOrStdin(oracle_rdbms_file, binary=False)
  try:
    oracle_rdbms_head_data = yaml.load(data)
  except Exception as e:
    raise ds_exceptions.ParseError('Cannot parse YAML:[{0}]'.format(e))

  oracle_rdbms_data = oracle_rdbms_head_data.get('oracle_rdbms',
                                                 oracle_rdbms_head_data)
  return ParseOracleSchemasListToOracleRdbmsMessage(messages, oracle_rdbms_data,
                                                    release_track)


def ParseOracleSchemasListToOracleRdbmsMessage(messages,
                                               oracle_rdbms_data,
                                               release_track=base.ReleaseTrack
                                               .BETA):
  """Parses an object of type {oracle_schemas: [...]} into the OracleRdbms message."""
  oracle_schemas_raw = oracle_rdbms_data.get('oracle_schemas', [])
  oracle_schema_msg_list = []
  for schema in oracle_schemas_raw:
    oracle_schema_msg_list.append(
        ParseOracleSchema(messages, schema, release_track))

  oracle_rdbms_msg = messages.OracleRdbms(
      oracleSchemas=oracle_schema_msg_list)
  return oracle_rdbms_msg


def UpdateV1alpha1ToV1MaskFields(field_mask):
  """Updates field mask paths according to the v1alpha1 > v1 Datastream API change.

  This allows for backwards compatibility with the current client field
  mask.

  Args:
    field_mask: List[str], list of stream fields to update

  Returns:
    updated_field_mask: List[str] field mask with fields translated
      from v1alpha1 API to v1.
  """
  updated_field_mask = []
  for path in field_mask:
    field_to_translate = None
    for field in _UPDATE_MASK_FIELD_TRANSLATION_V1ALPHA1_TO_V1:
      if field in path:
        field_to_translate = field
        break
    if field_to_translate:
      updated_field_mask.append(
          path.replace(
              field_to_translate,
              _UPDATE_MASK_FIELD_TRANSLATION_V1ALPHA1_TO_V1[field_to_translate])
      )
    else:
      updated_field_mask.append(path)
  return updated_field_mask


# TODO(b/207467120): deprecate BETA client.
def GetRDBMSV1alpha1ToV1FieldName(field, release_track):
  return RDBMS_FIELD_NAME_BY_RELEASE_TRACK.get(field,
                                               {}).get(release_track, field)


def _GetRDBMSFieldName(field, release_track):
  return RDBMS_FIELD_NAME_BY_RELEASE_TRACK.get(field,
                                               {}).get(release_track, field)
