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
"""API lib for Gemini Cloud Assist."""

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base


VERSION_MAP = {base.ReleaseTrack.BETA: 'v1beta'}


# The messages module can also be accessed from client.MESSAGES_MODULE
def GetMessagesModule(release_track=base.ReleaseTrack.BETA):
  """Returns the messages module for the given release track.

  Args:
    release_track: The release track to use.

  Returns:
    The messages module for the given release track.
  """
  return apis.GetMessagesModule('vectorsearch', VERSION_MAP.get(release_track))


def GetClientInstance(release_track=base.ReleaseTrack.BETA):
  """Returns the client instance for the given release track.

  Args:
    release_track: The release track to use.

  Returns:
    The client instance for the given release track.
  """
  return apis.GetClientInstance('vectorsearch', VERSION_MAP.get(release_track))
