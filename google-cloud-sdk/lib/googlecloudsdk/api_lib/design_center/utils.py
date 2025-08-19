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
"""Util for Design Center Cloud SDK."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


VERSION_MAP = {
    base.ReleaseTrack.ALPHA: 'v1alpha',
    # TODO(b/430098857): Add GA release track
    # base.ReleaseTrack.BETA: 'v1beta',
    # base.ReleaseTrack.GA: 'v1',
}


# The messages module can also be accessed from client.MESSAGES_MODULE
def GetMessagesModule(release_track=base.ReleaseTrack.ALPHA):
  api_version = VERSION_MAP.get(release_track)
  return apis.GetMessagesModule('designcenter', api_version)


def GetClientInstance(release_track=base.ReleaseTrack.ALPHA):
  api_version = VERSION_MAP.get(release_track)
  return apis.GetClientInstance('designcenter', api_version)


def GetLocationRef(args):
  """Returns a location reference."""
  location_ref = args.CONCEPTS.location.Parse()
  if not location_ref.Name():
    raise exceptions.InvalidArgumentException(
        'location', 'location id must be non-empty.'
    )
  return location_ref


def GetProjectRef():
  """Returns a project reference."""
  return resources.REGISTRY.Parse(
      properties.VALUES.core.project.GetOrFail(),
      collection='designcenter.projects',
  )


def MakeGetUriFunc(collection, release_track=base.ReleaseTrack.ALPHA):
  """Returns a function which turns a resource into a uri."""

  def _GetUri(resource):
    api_version = VERSION_MAP.get(release_track)
    result = resources.Registry().ParseRelativeName(
        resource.name, collection=collection, api_version=api_version
    )
    return result.SelfLink()

  return _GetUri
