# -*- coding: utf-8 -*- #
# Copyright 2022 Google Inc. All Rights Reserved.
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
"""Anthos Policy Controller status API utilities."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base


def _GetApiVersionFromReleaseTrack(release_track):
  if release_track == base.ReleaseTrack.ALPHA:
    return 'v1alpha'
  raise ValueError('Invalid release track: ' + release_track)


def GetMessagesModule(release_track):
  """Returns the Policy Controller status API messages module."""
  return apis.GetMessagesModule(
      'anthospolicycontrollerstatus_pa',
      _GetApiVersionFromReleaseTrack(release_track))


def GetClientInstance(release_track):
  """Returns the Policy Controller status API client instance."""
  return apis.GetClientInstance(
      'anthospolicycontrollerstatus_pa',
      _GetApiVersionFromReleaseTrack(release_track))
