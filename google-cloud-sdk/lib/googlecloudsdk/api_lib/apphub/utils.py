# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""Util for Apphub Cloud SDK."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base
from googlecloudsdk.core import resources

VERSION_MAP = {
    base.ReleaseTrack.ALPHA: 'v1alpha',
}


# The messages module can also be accessed from client.MESSAGES_MODULE
def GetMessagesModule(release_track=base.ReleaseTrack.ALPHA):
  api_version = VERSION_MAP.get(release_track)
  return apis.GetMessagesModule('apphub', api_version)


def GetClientInstance(release_track=base.ReleaseTrack.ALPHA):
  api_version = VERSION_MAP.get(release_track)
  return apis.GetClientInstance('apphub', api_version)


def AddToUpdateMask(update_mask, field_name):
  if update_mask:
    update_mask += ','
  return update_mask + field_name


def GetOperationResource(operation, release_track=base.ReleaseTrack.ALPHA):
  """Converts an Operation to a Resource that can be used with `waiter.WaitFor`."""
  api_version = VERSION_MAP.get(release_track)
  return resources.Registry().ParseRelativeName(
      operation.name,
      'apphub.projects.locations.operations',
      api_version=api_version,
  )


def WaitForOperation(poller, operation, message, max_wait_sec):
  return waiter.WaitFor(
      poller,
      GetOperationResource(operation),
      message,
      max_wait_ms=max_wait_sec * 1000,
  )
