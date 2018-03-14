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
