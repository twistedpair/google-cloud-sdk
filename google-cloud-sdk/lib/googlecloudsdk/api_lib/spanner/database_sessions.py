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
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


def Create(instance, database):
  """Create a database session."""
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')
  ref = resources.REGISTRY.Parse(
      database,
      params={
          'projectsId': properties.VALUES.core.project.GetOrFail,
          'instancesId': instance
      },
      collection='spanner.projects.instances.databases')
  req = msgs.SpannerProjectsInstancesDatabasesSessionsCreateRequest(
      database=ref.RelativeName())
  return client.projects_instances_databases_sessions.Create(req)


def Delete(session):
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')
  req = msgs.SpannerProjectsInstancesDatabasesSessionsDeleteRequest(
      name=session.name)
  return client.projects_instances_databases_sessions.Delete(req)


def ExecuteSql(session, sql, query_mode):
  """Execute an SQL command.

  Args:
    session: Session, Indicates that the repo should be created if
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

  req = msgs.SpannerProjectsInstancesDatabasesSessionsExecuteSqlRequest(
      session=session.name,
      executeSqlRequest=msgs.ExecuteSqlRequest(
          sql=sql,
          queryMode=msgs.ExecuteSqlRequest.QueryModeValueValuesEnum(
              query_mode)))
  resp = client.projects_instances_databases_sessions.ExecuteSql(req)
  return resp
