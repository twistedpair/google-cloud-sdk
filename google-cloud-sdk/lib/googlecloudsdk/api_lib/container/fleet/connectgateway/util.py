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
"""Connect Gateway API utils."""

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base

VERSION_MAP = {
    base.ReleaseTrack.ALPHA: 'v1alpha1',
    base.ReleaseTrack.BETA: 'v1beta1',
    base.ReleaseTrack.GA: 'v1',
}


# The messages module can also be accessed from client.MESSAGES_MODULE
def GetMessagesModule(release_track=base.ReleaseTrack.GA):
  api_version = VERSION_MAP.get(release_track)
  return apis.GetMessagesModule('connectgateway', api_version)


def GetClientInstance(release_track=base.ReleaseTrack.GA):
  api_version = VERSION_MAP.get(release_track)
  return apis.GetClientInstance('connectgateway', api_version)
