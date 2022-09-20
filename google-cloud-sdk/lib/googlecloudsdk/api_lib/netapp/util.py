# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Useful commands for interacting with the Cloud NetApp Files API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from typing import Any
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base


# TODO(b/239613419), when ready, introduce BETA and GA release tracks
VERSION_MAP = {base.ReleaseTrack.ALPHA: "v1alpha1"}


# The messages module can also be accessed from client.MESSAGES_MODULE
def GetMessagesModule(
    release_track: base.ReleaseTrack = base.ReleaseTrack.ALPHA) -> Any:
  """Import and return the appropriate NetApp messages module."""
  api_version: str = VERSION_MAP.get(release_track)
  return apis.GetMessagesModule(api_name="netapp", api_version=api_version)


def GetClientInstance(
    release_track: base.ReleaseTrack = base.ReleaseTrack.ALPHA) -> Any:
  api_version = VERSION_MAP.get(release_track)
  return apis.GetClientInstance(api_name="netapp", api_version=api_version)
