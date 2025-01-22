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
"""Shared utilities to access the Google Model Armor API."""


from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base


def GetClient(version=None):
  """Get the default client."""
  return apis.GetClientInstance(
      'modelarmor', version or apis.ResolveVersion('modelarmor')
  )


class Client(object):
  """Base class for all clients."""

  def __init__(self, client=None, messages=None, api_version=None):
    self.client = client or GetClient(version=api_version)
    self.messages = messages or self.client.MESSAGES_MODULE


class FloorSettings(Client):
  """High-level client for floor-settings."""

  def __init__(self, client=None, messages=None, api_version=None):
    client = client or GetClient(version=api_version)
    super(FloorSettings, self).__init__(client, messages)
    self.service = self.client.projects_locations

  def Get(self, name):
    """Get the floor-setting with the given name."""
    self.service = self.client.projects_locations
    req = self.messages.ModelarmorProjectsLocationsGetFloorSettingRequest(
        name=name
    )
    return self.service.GetFloorSetting(req)

  def Update(self, name, floor_setting, update_mask):
    """Update the floor-setting with the given name."""
    self.service = self.client.folders_locations
    req = self.messages.ModelarmorFoldersLocationsUpdateFloorSettingRequest(
        floorSetting=floor_setting,
        name=name,
        updateMask=','.join(update_mask),
    )
    return self.service.UpdateFloorSetting(req)

  def GetMessages(self):
    """Returns the messages module for the given version."""
    return self.messages


def GetApiFromTrack(track):
  """Returns api version based on the track."""
  if track == base.ReleaseTrack.ALPHA:
    return 'v1alpha'
  elif track == base.ReleaseTrack.GA:
    return 'v1'
