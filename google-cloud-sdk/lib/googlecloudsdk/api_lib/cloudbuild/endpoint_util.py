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
"""Utilities for operating on different endpoints."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import contextlib

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from six.moves.urllib import parse

_API_NAME = 'cloudbuild'
_API_VERSION = 'v1'
_UNIVERSE_DOMAIN = properties.VALUES.core.universe_domain.Get()


def DeriveCloudBuildREPEndpoint(endpoint, region):
  scheme, netloc, _, params, query, fragment = parse.urlparse(endpoint)
  service_name = netloc.split('.')[0]
  netloc = f'{service_name}.{region}.rep.{_UNIVERSE_DOMAIN}/'
  return parse.urlunparse((scheme, netloc, '', params, query, fragment))


@contextlib.contextmanager
def CloudBuildEndpointOverrides(region=None):
  """Context manager to override the Cloud Build endpoints for a while.

  Args:
    region: str, region of the Cloud Build endpoint.

  Yields:
    None.
  """
  used_endpoint = GetEffectiveCloudBuildEndpoint(region)
  old_endpoint = properties.VALUES.api_endpoint_overrides.cloudbuild.Get()
  if old_endpoint is not None:
    log.status.Print(
        'Using set api_endpoint_overrides [{}]'.format(old_endpoint)
    )
  try:
    if region and region != 'global' and old_endpoint is None:
      log.status.Print('Using endpoint [{}]'.format(used_endpoint))
      properties.VALUES.api_endpoint_overrides.cloudbuild.Set(used_endpoint)
    yield
  finally:
    old_endpoint = properties.VALUES.api_endpoint_overrides.cloudbuild.Set(
        old_endpoint
    )


def GetEffectiveCloudBuildEndpoint(region):
  """Returns regional Cloud Build Endpoint, or global if region not set."""

  endpoint = apis.GetEffectiveApiEndpoint(_API_NAME, _API_VERSION)
  if region and region != 'global':
    return DeriveCloudBuildREPEndpoint(endpoint, region)
  return endpoint
