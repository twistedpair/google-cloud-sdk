# -*- coding: utf-8 -*- #
# Copyright 2016 Google Inc. All Rights Reserved.
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
"""Spanner database sessions API helper."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import encoding
from apitools.base.py import extra_types
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis


def Create(database_ref):
  """Create a database session."""
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')
  req = msgs.SpannerProjectsInstancesDatabasesSessionsCreateRequest(
      database=database_ref.RelativeName())
  return client.projects_instances_databases_sessions.Create(req)


def List(database_ref, server_filter=None):
  """Lists all active sessions on the given database."""
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')
  req = msgs.SpannerProjectsInstancesDatabasesSessionsListRequest(
      database=database_ref.RelativeName(), filter=server_filter)

  return list_pager.YieldFromList(
      client.projects_instances_databases_sessions,
      req,
      # There is a batch_size_attribute ('pageSize') but we want to yield as
      # many results as possible per request.
      batch_size_attribute=None,
      field='sessions')


def Delete(session_ref):
  """Delete a database session."""
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')
  req = msgs.SpannerProjectsInstancesDatabasesSessionsDeleteRequest(
      name=session_ref.RelativeName())
  return client.projects_instances_databases_sessions.Delete(req)


def ExecuteSql(session_ref, sql, query_mode):
  """Execute an SQL command.

  Args:
    session_ref: Session, Indicates that the repo should be created if
        it does not exist.
    sql: String, The SQL to execute.
    query_mode: String, The mode in which to run the query. Must be one
        of 'NORMAL', 'PLAN', or 'PROFILE'
  Returns:
    (Repo) The capture repository.
  """
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')

  # TODO(b/33482229): remove this workaround
  def _ToJson(msg):
    return extra_types.JsonProtoEncoder(
        extra_types.JsonArray(entries=msg.entry))
  def _FromJson(data):
    return msgs.ResultSet.RowsValueListEntry(
        entry=extra_types.JsonProtoDecoder(data).entries)
  encoding.RegisterCustomMessageCodec(
      encoder=_ToJson, decoder=_FromJson)(
          msgs.ResultSet.RowsValueListEntry)

  execute_sql_request = msgs.ExecuteSqlRequest(
      sql=sql,
      queryMode=msgs.ExecuteSqlRequest.QueryModeValueValuesEnum(query_mode))
  req = msgs.SpannerProjectsInstancesDatabasesSessionsExecuteSqlRequest(
      session=session_ref.RelativeName(), executeSqlRequest=execute_sql_request)
  resp = client.projects_instances_databases_sessions.ExecuteSql(req)
  return resp


def Commit(session_ref, mutations):
  """Commit a transaction through a session.

  In Cloud Spanner, each session can have at most one active transaction at a
  time. In order to avoid retrying aborted transactions by accident, this
  request uses a temporary single use transaction instead of a previously
  started transaction to execute the mutations.
  Note: this commit is non-idempotent.

  Args:
    session_ref: Session, through which the transaction would be committed.
    mutations: A list of mutations, each represents a modification to one or
        more Cloud Spanner rows.

  Returns:
    The Cloud Spanner timestamp at which the transaction committed.
  """
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')

  req = msgs.SpannerProjectsInstancesDatabasesSessionsCommitRequest(
      session=session_ref.RelativeName(),
      commitRequest=msgs.CommitRequest(
          mutations=mutations,
          singleUseTransaction=msgs.TransactionOptions(
              readWrite=msgs.ReadWrite())))
  resp = client.projects_instances_databases_sessions.Commit(req)
  return resp


class MutationFactory(object):
  """Factory that creates and returns a mutation object in Cloud Spanner.

  A Mutation represents a sequence of inserts, updates and deletes that can be
  applied to rows and tables in a Cloud Spanner database.
  """
  msgs = apis.GetMessagesModule('spanner', 'v1')

  @classmethod
  def Insert(cls, table, data):
    """Constructs an INSERT mutation, which inserts a new row in a table.

    Args:
      table: String, the name of the table.
      data: A collections.OrderedDict, the keys of which are the column names
        and values are the column values to be inserted.

    Returns:
      An insert mutation operation.
    """
    return cls.msgs.Mutation(insert=cls._GetWrite(table, data))

  @classmethod
  def Update(cls, table, data):
    """Constructs an UPDATE mutation, which updates a row in a table.

    Args:
      table: String, the name of the table.
      data: An ordered dictionary where the keys are the column names and values
        are the column values to be updated.

    Returns:
      An update mutation operation.
    """
    return cls.msgs.Mutation(update=cls._GetWrite(table, data))

  @classmethod
  def Delete(cls, table, keys):
    """Constructs a DELETE mutation, which deletes a row in a table.

    Args:
      table: String, the name of the table.
      keys: String list, the primary key values of the row to delete.

    Returns:
      A delete mutation operation.
    """
    return cls.msgs.Mutation(delete=cls._GetDelete(table, keys))

  @classmethod
  def _GetWrite(cls, table, data):
    """Constructs Write object, which is needed for insert/update operations."""
    # TODO(b/33482229): a workaround to handle JSON serialization
    def _ToJson(msg):
      return extra_types.JsonProtoEncoder(
          extra_types.JsonArray(entries=msg.entry))

    encoding.RegisterCustomMessageCodec(
        encoder=_ToJson, decoder=None)(
            cls.msgs.Write.ValuesValueListEntry)

    json_columns = table.GetJsonData(data)
    json_column_names = [col.col_name for col in json_columns]
    json_column_values = [col.col_value for col in json_columns]

    return cls.msgs.Write(
        columns=json_column_names,
        table=table.name,
        values=[cls.msgs.Write.ValuesValueListEntry(entry=json_column_values)])

  @classmethod
  def _GetDelete(cls, table, keys):
    """Constructs Delete object, which is needed for delete operation."""

    # TODO(b/33482229): a workaround to handle JSON serialization
    def _ToJson(msg):
      return extra_types.JsonProtoEncoder(
          extra_types.JsonArray(entries=msg.entry))

    encoding.RegisterCustomMessageCodec(
        encoder=_ToJson, decoder=None)(
            cls.msgs.KeySet.KeysValueListEntry)

    key_set = cls.msgs.KeySet(keys=[
        cls.msgs.KeySet.KeysValueListEntry(entry=table.GetJsonKeys(keys))
    ])

    return cls.msgs.Delete(table=table.name, keySet=key_set)
