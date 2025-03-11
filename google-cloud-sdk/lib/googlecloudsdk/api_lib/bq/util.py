# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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

"""API lib for BigQuery."""

from googlecloudsdk.api_lib.util import apis


_BQ_API = 'bigquery'
_BQ_API_VERSION = 'v2'
_BQ_MIGRATION_API = 'bigquerymigration'
_BQ_MIGRATION_API_VERSION = 'v2'


def GetApiMessage(message_name, api=_BQ_API, api_version=_BQ_API_VERSION):
  """Return apitools message object for give message name."""
  messages = apis.GetMessagesModule(api, api_version)
  return getattr(messages, message_name)


def GetApiClient(api=_BQ_API, api_version=_BQ_API_VERSION):
  return apis.GetClientInstance(api, api_version)


def GetMigrationApiMessage(
    message_name, api=_BQ_MIGRATION_API, api_version=_BQ_MIGRATION_API_VERSION
):
  return GetApiMessage(message_name, api, api_version)


def GetMigrationApiClient():
  return GetApiClient(
      api=_BQ_MIGRATION_API, api_version=_BQ_MIGRATION_API_VERSION
  )
