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
"""Network Policy."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.compute import client_adapter


class NetworkPolicy:
  """Abstracts a network policy resource."""

  def __init__(self, ref, compute_client: client_adapter.ClientAdapter):
    self.ref = ref
    self._compute_client = compute_client

  @property
  def _client(self):
    return self._compute_client.apitools_client

  @property
  def _messages(self):
    return self._compute_client.messages

  def Create(self, network_policy, only_generate_request=False):
    """Sends request to create a network policy."""
    requests = [self._MakeCreateRequestTuple(network_policy=network_policy)]
    if only_generate_request:
      return requests
    return self._compute_client.MakeRequests(requests)

  def _MakeCreateRequestTuple(self, network_policy):
    return (
        self._client.regionNetworkPolicies,
        'Insert',
        self._messages.ComputeRegionNetworkPoliciesInsertRequest(
            networkPolicy=network_policy,
            project=self.ref.project,
            region=self.ref.region,
        ),
    )

  def Delete(self, only_generate_request=False):
    """Sends request to create a network policy."""
    requests = [self._MakeDeleteRequestTuple(network_policy=self.ref.Name())]
    if only_generate_request:
      return requests
    return self._compute_client.MakeRequests(requests)

  def _MakeDeleteRequestTuple(self, network_policy: str):
    return (
        self._client.regionNetworkPolicies,
        'Delete',
        self._messages.ComputeRegionNetworkPoliciesDeleteRequest(
            networkPolicy=network_policy,
            project=self.ref.project,
            region=self.ref.region,
        ),
    )
