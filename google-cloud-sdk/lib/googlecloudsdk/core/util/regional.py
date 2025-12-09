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

"""Regional endpoint utilities."""

import re


def LocationToRegion(location):
  """Returns the region corresponding to the given location.

  The location may be a zone, region, or multi-region as defined in
  go/gcp-locales. Note that not all Google-Managed Multi-Regions (GMMRs) are
  valid Standard Managed Multi-Regions (SMMRs); only the latter can be used for
  regional endpoints.

  GCP Regions: Follow the scheme:
    <geographical area>-<direction><index>
    (e.g. europe-north1, us-west4).
  GCP Zones: Follow the scheme:
    <region name>-<letter indicator>
    (e.g. europe-west1-a). A special case exists for AI Zones, which use:
    <region name>-ai<location_number><zone_letter>
    (e.g. us-central1-ai1a).
    Zones always end with a hyphen followed by a letter, or the special AI zone
    format.
  Multi-Regions (GMMRs): Have no strict naming convention and can be names like
    us, europe, nam-eur-asia1, etc.

  Args:
    location: str, Zone, region, or multi-region.
  Returns:
    str, Region (or multi-region) corresponding to the given location. Zones
      will be mapped to the region that contains them; regions or multi-regions
      will be returned as-is.
  """
  zone_regex = '([a-z]+-[a-z]+[0-9]+)-(?:[a-z]|ai[0-9]+[a-z])'
  if zone_match := re.fullmatch(zone_regex, location):
    # We assume something that looks like a zone is in fact a zone, and not a
    # multi-region. Unfortunately this is not guaranteed by the multi-region
    # naming specification (which doesn't exist at the time of this comment...),
    # so this assumption may become invalidated in the future. Note that
    # consuming the current authoritative list of GCP locales (as e.g. a build
    # dependency) is not a perfect solution either, since older versions of
    # gcloud would be unable to recognize new zones/regions that were turned up
    # later.
    region = zone_match.group(1)
  else:
    region = location
  return region
