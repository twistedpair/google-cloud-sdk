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
"""Database Migration Service conversion workspaces API clients and utilities.

ConversionWorkspacesClient provides access to all conversion workspaces APIs:
  - the conversion workspaces AI APIs,
  - the conversion workspaces CRUD APIs,
  - the conversion workspaces operations APIs,
  - the conversion workspaces entities APIs, and
  - the conversion workspaces LRO APIs.
"""

from googlecloudsdk.api_lib.database_migration.conversion_workspaces import conversion_workspaces_client

ConversionWorkspacesClient = (
    conversion_workspaces_client.ConversionWorkspacesClient
)
