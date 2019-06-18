# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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
"""Base of Flex API services."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base

API = 'composerflex'

ALPHA = 'v1alpha1'
BETA = 'v1beta1'
GA = 'v1'

RELEASE_TRACK_MAP = {
    base.ReleaseTrack.ALPHA: ALPHA,
    base.ReleaseTrack.BETA: BETA,
    base.ReleaseTrack.GA: GA,
}


def GetApiVersion(release_track=base.ReleaseTrack.GA):
  return RELEASE_TRACK_MAP.get(release_track, GA)


class Service(object):
  """Base class for Service definitions."""

  def __init__(self, api=API, release_track=base.ReleaseTrack.GA):
    self.api = api
    self.release_track = release_track
    self.version = GetApiVersion(self.release_track)
    self.client = apis.GetClientInstance(self.api, self.version)
    self.client_class = apis.GetClientClass(self.api, self.version)
    self.messages = apis.GetMessagesModule(self.api, self.version)
