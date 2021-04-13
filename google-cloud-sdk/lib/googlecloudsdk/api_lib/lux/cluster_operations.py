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
"""Lux instance operations API helper."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.lux import api_util
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.core import resources


def Await(operation, message):
  """Wait for the specified operation."""
  client = api_util.LuxClient(api_util.API_VERSION_DEFAULT)
  lux_client = client.lux_client
  poller = waiter.CloudOperationPoller(
      lux_client.projects_locations_clusters,
      lux_client.projects_locations_operations)
  ref = resources.REGISTRY.ParseRelativeName(
      operation.name,
      collection='luxadmin.projects.locations.operations')
  return waiter.WaitFor(poller, ref, message)
