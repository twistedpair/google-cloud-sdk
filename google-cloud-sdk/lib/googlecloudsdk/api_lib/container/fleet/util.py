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
"""Fleet API utils."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base
from googlecloudsdk.core import resources

VERSION_MAP = {
    base.ReleaseTrack.ALPHA: 'v1alpha',
    base.ReleaseTrack.BETA: 'v1beta',
    base.ReleaseTrack.GA: 'v1'
}


def GetMessagesModule(release_track=base.ReleaseTrack.ALPHA):
  return apis.GetMessagesModule('gkehub', VERSION_MAP[release_track])


def GetClientInstance(release_track=base.ReleaseTrack.ALPHA):
  return apis.GetClientInstance('gkehub', VERSION_MAP[release_track])


def GetClientClass(release_track=base.ReleaseTrack.ALPHA):
  return apis.GetClientClass('gkehub', VERSION_MAP[release_track])


def FleetResourceName(project,
                      fleet='default',
                      location='global',
                      release_track=base.ReleaseTrack.ALPHA):
  # See command_lib/container/fleet/resources.yaml
  return resources.REGISTRY.Parse(
      line=None,
      params={
          'projectsId': project,
          'locationsId': location,
          'fleetsId': fleet,
      },
      collection='gkehub.projects.locations.fleets',
      api_version=VERSION_MAP[release_track]
  ).RelativeName()


def FleetParentName(project,
                    fleet='default',
                    location='global',
                    release_track=base.ReleaseTrack.ALPHA):
  # See command_lib/container/fleet/resources.yaml
  return resources.REGISTRY.Parse(
      line=None,
      params={
          'projectsId': project,
          'locationsId': location,
          'fleetsId': fleet,
      },
      collection='gkehub.projects.locations.fleets',
      api_version=VERSION_MAP[release_track]
  ).RelativeName()
