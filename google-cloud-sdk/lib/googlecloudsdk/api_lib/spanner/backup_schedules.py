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
"""Cloud Spanner backup schedules API helper."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.util import apis


def Get(backup_schedule_ref):
  """Get a backup schedule."""
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')
  req = msgs.SpannerProjectsInstancesDatabasesBackupSchedulesGetRequest(
      name=backup_schedule_ref.RelativeName()
  )
  return client.projects_instances_databases_backupSchedules.Get(req)
