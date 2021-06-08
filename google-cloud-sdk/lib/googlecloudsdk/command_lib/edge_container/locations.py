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
"""Utilities for edge-container location commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections

from apitools.base.py import encoding

_Zone = collections.namedtuple('RedisZone', ['name', 'region'])


def ExtractZonesFromLocations(response, _):
  for region in response:
    if not region.metadata:
      continue

    metadata = encoding.MessageToDict(region.metadata)

    for zone in metadata.get('availableZones', []):
      yield _Zone(name=zone, region=region.locationId)


def ExtractZoneFromLocations(response, args):
  for region in response:
    if not region.metadata:
      continue

    metadata = encoding.MessageToDict(region.metadata)

    for zone_name, zone in metadata.get('availableZones', []).items():
      if zone_name == args.zone.split('/')[-1]:
        return zone
