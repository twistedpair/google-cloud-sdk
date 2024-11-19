# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Spanner database splits helper."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from googlecloudsdk.api_lib.spanner import database_sessions
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import resources


def AddSplitPoints(database_ref, split_points, initiator_string):
  """Add split points to a database."""
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')

  req = msgs.SpannerProjectsInstancesDatabasesAddSplitPointsRequest(
      database=database_ref.RelativeName()
  )
  req.addSplitPointsRequest = msgs.AddSplitPointsRequest()

  if initiator_string:
    req.addSplitPointsRequest.initiator = initiator_string

  req.addSplitPointsRequest.splitPoints = split_points
  return client.projects_instances_databases.AddSplitPoints(req)


def ListSplitPoints(database_ref):
  """List the user added split points fo a database."""
# TODO(b/362149997): Check this for both dialects.
  session_name = database_sessions.Create(database_ref, None)

  session = resources.REGISTRY.ParseRelativeName(
      relative_name=session_name.name,
      collection='spanner.projects.instances.databases.sessions',
  )
  try:
    return database_sessions.ExecuteSql(
        'SELECT * FROM SPANNER_SYS.USER_SPLIT_POINTS', 'NORMAL', session
    )
  finally:
    database_sessions.Delete(session)
