# -*- coding: utf-8 -*- #
#
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
"""Common utility functions for getting the Managed Flink API client."""
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base

VERSION_MAP = {
    base.ReleaseTrack.ALPHA: 'v1alpha',
    base.ReleaseTrack.BETA: 'v1beta',
    base.ReleaseTrack.GA: 'v1',
}


class FlinkClient(object):
  """Wrapper for Flink API client and associated resources."""

  def __init__(self, release_track):
    api_version = VERSION_MAP.get(release_track)
    self.release_track = release_track
    self.client = apis.GetClientInstance('managedflink', api_version)


# The messages module can also be accessed from client.MESSAGES_MODULE
def GetMessagesModule(release_track=base.ReleaseTrack.GA):
  api_version = VERSION_MAP.get(release_track)
  return apis.GetMessagesModule('managedflink', api_version)
