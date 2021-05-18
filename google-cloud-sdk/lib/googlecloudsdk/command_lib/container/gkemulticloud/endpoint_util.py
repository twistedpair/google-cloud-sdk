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
"""Utilities for operating on different endpoints."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import contextlib

from googlecloudsdk.api_lib.container.azure import util as azure_api_util
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base
from googlecloudsdk.core import properties
from six.moves.urllib import parse


def _AppendRegion(endpoint, region):
  scheme, netloc, path, params, query, fragment = parse.urlparse(endpoint)
  netloc = '{}-{}'.format(region, netloc)
  return parse.urlunparse((scheme, netloc, path, params, query, fragment))


@contextlib.contextmanager
def GkemulticloudEndpointOverride(region, track=base.ReleaseTrack.GA):
  """Context manager to override the GKE Multi-cloud endpoint temporarily.

  Args:
    region: str, region to use for GKE Multi-cloud.
    track: calliope_base.ReleaseTrack, Release track of the endpoint.

  Yields:
    None.
  """
  if not region:
    raise ValueError('A region must be specified.')

  original_ep = properties.VALUES.api_endpoint_overrides.gkemulticloud.Get()
  regional_ep = _GetEffectiveEndpoint(region, track=track)
  try:
    if not original_ep:
      properties.VALUES.api_endpoint_overrides.gkemulticloud.Set(regional_ep)
    yield
  finally:
    if not original_ep:
      properties.VALUES.api_endpoint_overrides.gkemulticloud.Set(original_ep)


def _GetEffectiveEndpoint(region, track=base.ReleaseTrack.GA):
  """Returns regional GKE Multi-cloud Endpoint."""
  endpoint = apis.GetEffectiveApiEndpoint(
      azure_api_util.MODULE_NAME, azure_api_util.GetApiVersionForTrack(track))
  return _AppendRegion(endpoint, region)
