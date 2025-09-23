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
from googlecloudsdk.api_lib.artifacts import exceptions as ar_exceptions
from googlecloudsdk.core import properties

# Rerouted regions are regions that don't have a regional endpoint
# and must be redirected to global region.
# go/rep-deployment-roadmap, go/rep-dashboards
_CONTAINER_ANALYSIS_REROUTED_LOCATIONS = frozenset([
    # TODO(b/445909332): REP is available. Turn up CA API RSLB.
    # go/keep-sorted start
    "eu",
    "europe-north2",
    "europe-west12",
    "northamerica-south1",
    "us",
    "us-west8",
    # go/keep-sorted end
    # No REP available.
    # go/keep-sorted start
    "asia",
    "asia-southeast3",
    "europe-west15",
    "global"
    # go/keep-sorted end
])

# Direct locations are regions and multi-regions that have regional endpoints.
_CONTAINER_ANALYSIS_DIRECT_LOCATIONS = frozenset([
    # go/keep-sorted start
    "africa-south1",
    "asia-east1",
    "asia-east2",
    "asia-northeast1",
    "asia-northeast2",
    "asia-northeast3",
    "asia-south1",
    "asia-south2",
    "asia-southeast1",
    "asia-southeast2",
    "australia-southeast1",
    "australia-southeast2",
    "europe-central2",
    "europe-north1",
    "europe-southwest1",
    "europe-west1",
    "europe-west10",
    "europe-west2",
    "europe-west3",
    "europe-west4",
    "europe-west6",
    "europe-west8",
    "europe-west9",
    "me-central1",
    "me-central2",
    "me-west1",
    "northamerica-northeast1",
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
    # go/keep-sorted end
])

_CONTAINER_ANALYSIS_REP_STRUCTURE = "https://containeranalysis.{}.rep.{}/"
_ARTIFACT_REGISTRY_FACADE_STRUCTURE = "{protocol}{prefix}{location}-{format}.{domain}"
_ARTIFACT_REGISTRY_FACADE_REP_STRUCTURE = "{protocol}{prefix}{format}.{location}.rep.{domain}"


def _GetRegionalEndpoint(region):
  universe_domain = properties.VALUES.core.universe_domain.Get()
  regional_endpoint = _CONTAINER_ANALYSIS_REP_STRUCTURE.format(
      region, universe_domain
  )
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
  elif (
      region not in _CONTAINER_ANALYSIS_DIRECT_LOCATIONS
      and region not in _CONTAINER_ANALYSIS_REROUTED_LOCATIONS
  ):
    raise ar_exceptions.UnsupportedLocationError()
  elif (
      override is None and region not in _CONTAINER_ANALYSIS_REROUTED_LOCATIONS
  ):
    regional_endpoint = _GetRegionalEndpoint(region)
    properties.VALUES.api_endpoint_overrides.containeranalysis.Set(
        regional_endpoint
    )
  try:
    yield
  finally:
    properties.VALUES.api_endpoint_overrides.containeranalysis.Set(override)


def ArtifactRegistryDomainEndpoint(
    location, repo_format, protocol="", rep=False,
):
  """Returns the Artifact Registry domain endpoint for the given region."""
  # TODO(b/399155579): read from universe descriptor once AR is added.
  domain = "pkg.dev"
  prefix = properties.VALUES.artifacts.registry_endpoint_prefix.Get()
  if protocol:
    if protocol != "https" and protocol != "http":
      raise ar_exceptions.ArtifactRegistryError(
          "Invalid protocol: {}, must be https or http".format(protocol)
      )
    protocol = protocol + "://"
  template = (
      _ARTIFACT_REGISTRY_FACADE_REP_STRUCTURE
      if rep
      else _ARTIFACT_REGISTRY_FACADE_STRUCTURE
  )
  return template.format(
      protocol=protocol,
      prefix=prefix,
      location=location,
      format=repo_format,
      domain=domain,
  )
