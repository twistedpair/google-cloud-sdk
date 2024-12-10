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
"""Utilities for the Resource Settings service."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.util import apis

RESOURCE_SETTINGS_API_NAME = 'cloudresourcemanager'
RESOURCE_SETTINGS_API_VERSION = 'v3'


def ResourceSettingsClient():
  """Returns a client instance of the Resource Settings service."""
  return apis.GetClientInstance(RESOURCE_SETTINGS_API_NAME,
                                RESOURCE_SETTINGS_API_VERSION)


def ResourceSettingsMessages():
  """Returns the messages module for the Resource Settings service."""
  return apis.GetMessagesModule(RESOURCE_SETTINGS_API_NAME,
                                RESOURCE_SETTINGS_API_VERSION)


# Folders Settings
def FoldersSettingsService():
  """Returns the service class for the Folders Settings resource."""
  client = ResourceSettingsClient()
  return client.folders_settings


# Folders Effective Settings
def FoldersEffectiveSettingsService():
  """Returns the service class for the Folders Effective Settings resource."""
  client = ResourceSettingsClient()
  return client.folders_effectiveSettings


# Organization Settings
def OrganizationsSettingsService():
  """Returns the service class for the Organization Settings resource."""
  client = ResourceSettingsClient()
  return client.organizations_settings


# Organization Effective Settings
def OrganizationsEffectiveSettingsService():
  """Returns the service class for the Organization Effective Settings resource."""
  client = ResourceSettingsClient()
  return client.organizations_effectiveSettings


# Project Settings
def ProjectsSettingsService():
  """Returns the service class for the Project Settings resource."""
  client = ResourceSettingsClient()
  return client.projects_settings


# Project Effective Settings
def ProjectsEffectiveSettingsService():
  """Returns the service class for the Project Effective Settings resource."""
  client = ResourceSettingsClient()
  return client.projects_effectiveSettings
