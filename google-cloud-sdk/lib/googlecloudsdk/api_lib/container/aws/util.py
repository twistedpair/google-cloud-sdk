# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Utilities Cloud GKE Multi-cloud for AWS API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base

MODULE_NAME = 'gkemulticloud'

_RELEASE_TRACK_TO_API_VERSION = {
    base.ReleaseTrack.ALPHA: 'v1',
    base.ReleaseTrack.BETA: 'v1',
    base.ReleaseTrack.GA: 'v1',
}


def GetApiVersionForTrack(release_track=base.ReleaseTrack.GA):
  """Returns the API version for a release track."""
  return _RELEASE_TRACK_TO_API_VERSION.get(release_track)


def GetMessagesModule(release_track=base.ReleaseTrack.GA):
  """Returns the API messages module for a release track."""
  api_version = _RELEASE_TRACK_TO_API_VERSION.get(release_track)
  return apis.GetMessagesModule(MODULE_NAME, api_version)


def GetClientInstance(release_track=base.ReleaseTrack.GA):
  """Returns the API client for a release track."""
  api_version = _RELEASE_TRACK_TO_API_VERSION.get(release_track)
  return apis.GetClientInstance(MODULE_NAME, api_version)
