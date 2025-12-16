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
"""A library dealing with Cloud Region naming."""

import re


class UnknownRegionError(Exception):
  """The region was not recognized."""

SHORT_CONTINENT_COUNTRY = {
    'africa': 'af',
    'asia': 'as',
    'antarctica': 'an',
    'australia': 'au',
    'europe': 'eu',
    'me': 'me',
    'northamerica': 'na',
    'southamerica': 'sa',
    'us': 'us',
    'france': 'fr',
    'germany': 'de',
}
SHORT_DIRECTION = {
    'north': 'n',
    'south': 's',
    'east': 'e',
    'west': 'w',
    'northeast': 'ne',
    'southeast': 'se',
    'northwest': 'nw',
    'southwest': 'sw',
    'central': 'c',
    'prp': 'p'
}
SHORT_PREFIX = {
    'tpcl-': 't-',
    'prp-': 'p-',
}


def ShortenGcpRegion(region):
  """Converts a GCP region to a shortened version or raises UnknownRegionError.

  Args:
    region: The GCP region like us-central1.

  Returns:
    The shortened region, like eu-c1 or us-se98.

  Raises:
    UnknownRegionError: If the region can not be deciphered.
  """
  prefix, continent_country, area, num, is_quarantine = _MatchRegion(region)

  try:
    short_continent_country = SHORT_CONTINENT_COUNTRY[continent_country]
    short_direction = SHORT_DIRECTION[area]
  except KeyError as e:
    raise UnknownRegionError(f'Incorrect cloud region name: {e}.') from None

  if prefix in SHORT_PREFIX:
    prefix = SHORT_PREFIX[prefix]

  if is_quarantine:
    prefix = 'q-'

  return f'{prefix}{short_continent_country}-{short_direction}{num}'


def _MatchRegion(region):
  """Extracts the fully qualified components of the provided region name."""
  match = re.fullmatch(r'([a-z]+-)?([a-z]+)-([a-z]+)(\d{1,2})(q)?', region)
  if not match:
    raise UnknownRegionError(f'Unable to parse region {region}')

  prefix, continent_country, area, index, is_quarantine = match.groups()
  if prefix is None:
    prefix = ''

  return prefix, continent_country, area, index, is_quarantine
