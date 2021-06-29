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
from googlecloudsdk.core import resources
from googlecloudsdk.core import yaml
from googlecloudsdk.core.console import console_io
import six

_DEFAULT_API_VERSION = 'v1alpha1'


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


def ParseMysqlColumn(messages, mysql_column_object):
  """Parses a raw mysql column json/yaml into the MysqlColumn message."""
  return messages.MysqlColumn(
      columnName=mysql_column_object.get('column_name', {}),
      dataType=mysql_column_object.get('data_type', {}),
      collation=mysql_column_object.get('collation', {}),
      length=mysql_column_object.get('length', {}),
      nullable=mysql_column_object.get('nullable', {}),
      ordinalPosition=mysql_column_object.get('ordinal_position', {}),
      primaryKey=mysql_column_object.get('primary_key', {}))


def ParseMysqlTable(messages, mysql_table_object):
  """Parses a raw mysql table json/yaml into the MysqlTable message."""
  mysql_column_msg_list = []
  for column in mysql_table_object.get('mysql_columns', []):
    mysql_column_msg_list.append(ParseMysqlColumn(messages, column))
  table_name = mysql_table_object.get('table_name')
  if not table_name:
    raise ds_exceptions.ParseError(
        'Cannot parse YAML: missing key "table_name".')
  return messages.MysqlTable(
      tableName=table_name,
      mysqlColumns=mysql_column_msg_list)


def ParseMysqlDatabase(messages, mysql_database_object):
  """Parses a raw mysql database json/yaml into the MysqlDatabase message."""
  mysql_tables_msg_list = []
  for table in mysql_database_object.get('mysql_tables', []):
    mysql_tables_msg_list.append(ParseMysqlTable(messages, table))
  database_name = mysql_database_object.get('database_name')
  if not database_name:
    raise ds_exceptions.ParseError(
        'Cannot parse YAML: missing key "database_name".')
  return messages.MysqlDatabase(
      databaseName=database_name,
      mysqlTables=mysql_tables_msg_list)


def ParseMysqlRdbmsFile(messages, mysql_rdbms_file):
  """Parses a mysql_rdbms_file into the MysqlRdbms message."""
  data = console_io.ReadFromFileOrStdin(mysql_rdbms_file, binary=False)
  try:
    mysql_rdbms_head_data = yaml.load(data)
  except Exception as e:
    raise ds_exceptions.ParseError('Cannot parse YAML:[{0}]'.format(e))

  mysql_rdbms_data = mysql_rdbms_head_data.get('mysql_rdbms',
                                               mysql_rdbms_head_data)
  return ParseMysqlSchemasListToMysqlRdbmsMessage(messages, mysql_rdbms_data)


def ParseMysqlSchemasListToMysqlRdbmsMessage(messages, mysql_rdbms_data):
  """Parses an object of type {mysql_databases: [...]} into the MysqlRdbms message."""
  mysql_databases_raw = mysql_rdbms_data.get('mysql_databases', [])
  mysql_database_msg_list = []
  for schema in mysql_databases_raw:
    mysql_database_msg_list.append(ParseMysqlDatabase(messages, schema))

  mysql_rdbms_msg = messages.MysqlRdbms(
      mysqlDatabases=mysql_database_msg_list)
  return mysql_rdbms_msg


def ParseOracleColumn(messages, oracle_column_object):
  """Parses a raw oracle column json/yaml into the OracleColumn message."""
  return messages.OracleColumn(
      columnName=oracle_column_object.get('column_name', {}),
      dataType=oracle_column_object.get('data_type', {}),
      encoding=oracle_column_object.get('encoding', {}),
      length=oracle_column_object.get('length', {}),
      nullable=oracle_column_object.get('nullable', {}),
      ordinalPosition=oracle_column_object.get('ordinal_position', {}),
      precision=oracle_column_object.get('precision', {}),
      primaryKey=oracle_column_object.get('primary_key', {}),
      scale=oracle_column_object.get('scale', {}))


def ParseOracleTable(messages, oracle_table_object):
  """Parses a raw oracle table json/yaml into the OracleTable message."""
  oracle_columns_msg_list = []
  for column in oracle_table_object.get('oracle_columns', []):
    oracle_columns_msg_list.append(ParseOracleColumn(messages, column))
  table_name = oracle_table_object.get('table_name')
  if not table_name:
    raise ds_exceptions.ParseError(
        'Cannot parse YAML: missing key "table_name".')
  return messages.OracleTable(
      tableName=table_name,
      oracleColumns=oracle_columns_msg_list)


def ParseOracleSchema(messages, oracle_schema_object):
  """Parses a raw oracle schema json/yaml into the OracleSchema message."""
  oracle_tables_msg_list = []
  for table in oracle_schema_object.get('oracle_tables', []):
    oracle_tables_msg_list.append(ParseOracleTable(messages, table))
  schema_name = oracle_schema_object.get('schema_name')
  if not schema_name:
    raise ds_exceptions.ParseError(
        'Cannot parse YAML: missing key "schema_name".')
  return messages.OracleSchema(
      schemaName=schema_name,
      oracleTables=oracle_tables_msg_list)


def ParseOracleRdbmsFile(messages, oracle_rdbms_file):
  """Parses a oracle_rdbms_file into the OracleRdbms message."""
  data = console_io.ReadFromFileOrStdin(oracle_rdbms_file, binary=False)
  try:
    oracle_rdbms_head_data = yaml.load(data)
  except Exception as e:
    raise ds_exceptions.ParseError('Cannot parse YAML:[{0}]'.format(e))

  oracle_rdbms_data = oracle_rdbms_head_data.get('oracle_rdbms',
                                                 oracle_rdbms_head_data)
  return ParseOracleSchemasListToOracleRdbmsMessage(messages, oracle_rdbms_data)


def ParseOracleSchemasListToOracleRdbmsMessage(messages, oracle_rdbms_data):
  """Parses an object of type {oracle_schemas: [...]} into the OracleRdbms message."""
  oracle_schemas_raw = oracle_rdbms_data.get('oracle_schemas', [])
  oracle_schema_msg_list = []
  for schema in oracle_schemas_raw:
    oracle_schema_msg_list.append(ParseOracleSchema(messages, schema))

  oracle_rdbms_msg = messages.OracleRdbms(
      oracleSchemas=oracle_schema_msg_list)
  return oracle_rdbms_msg
