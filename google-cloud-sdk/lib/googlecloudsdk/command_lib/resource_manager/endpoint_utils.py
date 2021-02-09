# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Utilities for handling location flag."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import contextlib

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import properties
from six.moves.urllib import parse

CRM_API_NAME = 'cloudresourcemanager'
CRM_API_VERSION = 'v3'


@contextlib.contextmanager
def CrmEndpointOverrides(location):
  """Context manager to override the current CRM endpoint.

  The new endpoint will temporarily be the one corresponding to the given
  location.

  Args:
    location: str, location of the CRM backend (e.g. a cloud region or zone).
      Can be None to indicate global.

  Yields:
    None.
  """
  endpoint_property = getattr(properties.VALUES.api_endpoint_overrides,
                              CRM_API_NAME)
  old_endpoint = endpoint_property.Get()
  try:
    if location and location != 'global':
      endpoint_property.Set(_GetEffectiveCrmEndpoint(location))
    yield
  finally:
    endpoint_property.Set(old_endpoint)


def _GetEffectiveCrmEndpoint(location):
  """Returns regional Tag Bindings Endpoint based on the regional location."""
  endpoint = apis.GetEffectiveApiEndpoint(CRM_API_NAME, CRM_API_VERSION)
  return _DeriveCrmRegionalEndpoint(endpoint, location)


def _DeriveCrmRegionalEndpoint(endpoint, location):
  scheme, netloc, path, params, query, fragment = parse.urlparse(endpoint)
  netloc = '{}-{}'.format(location, netloc)
  return parse.urlunparse((scheme, netloc, path, params, query, fragment))
