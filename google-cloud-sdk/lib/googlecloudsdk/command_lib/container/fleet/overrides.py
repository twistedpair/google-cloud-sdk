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
from googlecloudsdk.command_lib.container.fleet.memberships import util as memberships_util
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
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
    self.endpoint: str = None
    # The Connect Gateway endpoint override property.
    self.override = properties.VALUES.api_endpoint_overrides.Property(
        self.API_NAME
    )
    self._original_endpoint: str = None

  def __enter__(self):
    if self.override.IsExplicitlySet():
      log.warning(
          'You are running this command with the `connectgateway` endpoint'
          ' override set. Ensure you are using the correct regional endpoint.'
          ' If you are only trying to change your environment, set only the'
          ' `gkehub` endpoint override and not the `connectgateway` endpoint'
          ' override.'
      )
      return

    try:
      hub_override = properties.VALUES.api_endpoint_overrides.Property(
          gkehub_api_util.GKEHUB_API_NAME
      ).Get()
    except properties.NoSuchPropertyError:
      hub_override = None

    subdomain = memberships_util.GetConnectGatewayServiceName(
        hub_override, self.region
    )
    self.endpoint = f'https://{subdomain}/'
    self._original_endpoint = self.override.Get()
    self.override.Set(self.endpoint)
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.override.Set(self._original_endpoint)
