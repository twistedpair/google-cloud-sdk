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
"""Utilities for handling API endpoint overrides."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.container.fleet import gkehub_api_util
from googlecloudsdk.api_lib.container.fleet.connectgateway import util as connectgateway_api_util
from googlecloudsdk.api_lib.util import apis as core_apis
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import properties


class RegionalGatewayEndpoint:
  """Context manager for connecting to a particular regional Connect Gateway endpoint.

  This uses the provided region to temporarily override
  `api_endpoint_overrides/connectgateway` to a regional endpoint. If the
  `gkehub` endpoint is overridden, the `connectgateway` endpoint will use the
  same environment.

  This context manager is a no-op if the `connectgateway` endpoint is already
  overridden.
  """

  API_NAME = connectgateway_api_util.API_NAME
  API_VERSION = connectgateway_api_util.VERSION_MAP[
      connectgateway_api_util.DEFAULT_TRACK
  ]

  def __init__(self, region: str):
    """Initializes the context manager.

    Args:
      region: The Connect Gateway region to connect to.

    Raises:
      exceptions.Error: If `region` is Falsy.
    """

    if not region:
      raise exceptions.Error(
          'A region must be provided for the Gateway endpoint.'
      )
    self.region = region
    # The overridden endpoint value.
    self.endpoint: str = ''
    # The Connect Gateway endpoint override property.
    self.override = properties.VALUES.api_endpoint_overrides.Property(
        self.API_NAME
    )
    self._original_endpoint: str = ''

  def __enter__(self):
    try:
      hub_override = properties.VALUES.api_endpoint_overrides.Property(
          gkehub_api_util.GKEHUB_API_NAME
      ).Get()
      hub_version = gkehub_api_util.GKEHUB_GA_API_VERSION
    except properties.NoSuchPropertyError:
      hub_override = None
      hub_version = None

    if hub_override:
      subdomain_endpoint = core_apis.GetEffectiveApiEndpoint(
          gkehub_api_util.GKEHUB_API_NAME, hub_version
      )
    else:
      subdomain_endpoint = core_apis.GetEffectiveApiEndpoint(
          self.API_NAME, self.API_VERSION
      )

    if hub_override:
      subdomain_endpoint = hub_override.replace('gkehub', 'connectgateway')
    if self.region == 'global' or self.region in subdomain_endpoint:
      self.endpoint = subdomain_endpoint
    else:
      if subdomain_endpoint.startswith('https://'):
        self.endpoint = f'https://{self.region}-{subdomain_endpoint[8:]}'
      elif subdomain_endpoint.startswith('http://'):
        self.endpoint = f'http://{self.region}-{subdomain_endpoint[7:]}'
      else:
        raise exceptions.Error(
            f'Invalid Connect Gateway endpoint: {subdomain_endpoint}'
        )

    self._original_endpoint = self.override.Get()
    self.override.Set(self.endpoint)
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.override.Set(self._original_endpoint)
