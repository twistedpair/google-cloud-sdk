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
# Lint as: python3
"""Utilities for operating on different endpoints."""

import contextlib
from googlecloudsdk.api_lib.artifacts import exceptions as aa_exceptions
from googlecloudsdk.core import properties

# Rerouted regions are regions that don't have a regional endpoint
# and must be redirected to global region.
_REROUTED_LOCATIONS = frozenset([
    "africa-south1",
    "asia-northeast2",
    "australia-southeast2",
    "europe-west10",
    "europe-west12",
    "us-west8",
    "us",
    "eu",
    "asia",
    "global"
])

# Direct locations are regions and multi-regions that have regional endpoints.
_DIRECT_LOCATIONS = frozenset([
    "asia-east1",
    "asia-east2",
    "asia-northeast1",
    "asia-northeast3",
    "asia-south1",
    "asia-south2",
    "asia-southeast1",
    "asia-southeast2",
    "australia-southeast1",
    "europe-central2",
    "europe-north1",
    "europe-southwest1",
    "europe-west1",
    "europe-west2",
    "europe-west3",
    "europe-west4",
    "europe-west6",
    "europe-west8",
    "europe-west9",
    "me-central1",
    "me-central2",
    "me-west1northamerica-northeast1",
    "northamerica-northeast2",
    "southamerica-east1",
    "southamerica-west1",
    "us-central1",
    "us-central2",
    "us-east1",
    "us-east4",
    "us-east5",
    "us-east7",
    "us-south1",
    "us-west1",
    "us-west2",
    "us-west3",
    "us-west4",
])

_REP_STRUCTURE = "https://containeranalysis.{}.rep.{}/"


def _GetRegionalEndpoint(region):
  universe_domain = properties.VALUES.core.universe_domain.Get()
  regional_endpoint = _REP_STRUCTURE.format(region, universe_domain)
  return regional_endpoint


@contextlib.contextmanager
def WithRegion(region=None):
  """WithRegion overrides artifact analysis endpoint with endpoint of region.

  A call to WithRegion should be done in a with clause.
  If an existing override exists, this command does not do anything.
  If a rerouted region is passed in, this command does not do anything.
  An error is raised if an invalid location is passed in.

  Args:
    region: str, location

  Raises:
    aa_exceptions.UnsupportedLocationError if location provided is invalid.

  Yields:
    None
  """
  override = properties.VALUES.api_endpoint_overrides.containeranalysis.Get()
  if region is None:
    pass
  elif region not in _DIRECT_LOCATIONS and region not in _REROUTED_LOCATIONS:
    raise aa_exceptions.UnsupportedLocationError()
  elif override is None and region not in _REROUTED_LOCATIONS:
    regional_endpoint = _GetRegionalEndpoint(region)
    properties.VALUES.api_endpoint_overrides.containeranalysis.Set(
        regional_endpoint)
  try:
    yield
  finally:
    properties.VALUES.api_endpoint_overrides.containeranalysis.Set(override)
