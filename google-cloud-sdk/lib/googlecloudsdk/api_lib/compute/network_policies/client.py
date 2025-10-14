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

  def Describe(self, only_generate_request=False):
    """Sends request to describe a network policy."""
    requests = [self._MakeGetRequestTuple(network_policy=self.ref.Name())]
    if only_generate_request:
      return requests
    return self._compute_client.MakeRequests(requests)

  def _MakeGetRequestTuple(self, network_policy: str):
    return (
        self._client.regionNetworkPolicies,
        'Get',
        self._messages.ComputeRegionNetworkPoliciesGetRequest(
            networkPolicy=network_policy,
            project=self.ref.project,
            region=self.ref.region,
        ),
    )

  def Update(self, network_policy):
    """Sends request to update a network policy."""
    requests = [self._MakePatchRequestTuple(network_policy=network_policy)]
    return self._compute_client.MakeRequests(requests)

  def _MakePatchRequestTuple(self, network_policy):
    return (
        self._client.regionNetworkPolicies,
        'Patch',
        self._messages.ComputeRegionNetworkPoliciesPatchRequest(
            networkPolicy=self.ref.Name(),
            networkPolicyResource=network_policy,
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

  def AddAssociation(
      self, association, network_policy, only_generate_request=False
  ):
    """Sends request to add an association to a network policy."""
    requests = [
        self._MakeAddAssociationRequestTuple(
            association=association, network_policy=network_policy
        )
    ]
    if only_generate_request:
      return requests
    return self._compute_client.MakeRequests(requests)

  def _MakeAddAssociationRequestTuple(self, association, network_policy: str):
    return (
        self._client.regionNetworkPolicies,
        'AddAssociation',
        self._messages.ComputeRegionNetworkPoliciesAddAssociationRequest(
            networkPolicy=network_policy,
            networkPolicyAssociation=association,
            project=self.ref.project,
            region=self.ref.region,
        ),
    )

  def RemoveAssociation(
      self,
      *,
      association: str,
      network_policy: str,
      only_generate_request=False,
  ):
    """Sends request to delete an association to a network policy."""
    requests = [
        self._MakeRemoveAssociationRequestTuple(
            association=association, network_policy=network_policy
        )
    ]
    if only_generate_request:
      return requests
    return self._compute_client.MakeRequests(requests)

  def _MakeRemoveAssociationRequestTuple(
      self, association: str, network_policy: str
  ):
    return (
        self._client.regionNetworkPolicies,
        'RemoveAssociation',
        self._messages.ComputeRegionNetworkPoliciesRemoveAssociationRequest(
            networkPolicy=network_policy,
            name=association,
            project=self.ref.project,
            region=self.ref.region,
        ),
    )

  def GetAssociation(
      self, *, name: str, network_policy: str, only_generate_request=False
  ):
    """Sends request to get an association to a network policy."""
    requests = [
        self._MakeGetAssociationRequestTuple(
            association=name, network_policy=network_policy
        )
    ]
    if only_generate_request:
      return requests
    return self._compute_client.MakeRequests(requests)

  def _MakeGetAssociationRequestTuple(
      self, association: str, network_policy: str
  ):
    return (
        self._client.regionNetworkPolicies,
        'GetAssociation',
        self._messages.ComputeRegionNetworkPoliciesGetAssociationRequest(
            networkPolicy=network_policy,
            name=association,
            project=self.ref.project,
            region=self.ref.region,
        ),
    )


class NetworkPolicyRule(NetworkPolicy):
  """Abstracts Network Policy Rule."""

  def __init__(self, ref=None, compute_client=None):
    super().__init__(ref=ref, compute_client=compute_client)

  def CreateRule(
      self,
      network_policy=None,
      network_policy_rule=None,
      only_generate_request=False,
  ):
    """Sends request to create an network policy rule."""
    request = [
        self._MakeCreateRuleRequestTuple(
            network_policy=network_policy,
            network_policy_rule=network_policy_rule,
        )
    ]
    if only_generate_request:
      return request
    return self._compute_client.MakeRequests(request)

  def _MakeCreateRuleRequestTuple(
      self, network_policy=None, network_policy_rule=None
  ):
    return (
        self._client.regionNetworkPolicies,
        'AddTrafficClassificationRule',
        self._messages.ComputeRegionNetworkPoliciesAddTrafficClassificationRuleRequest(
            networkPolicy=network_policy,
            networkPolicyTrafficClassificationRule=network_policy_rule,
            project=self.ref.project,
            region=self.ref.region,
        ),
    )

  def DeleteRule(
      self,
      network_policy,
      priority,
  ):
    """Sends request to delete an network policy rule."""
    request = [
        self._MakeDeleteRuleRequestTuple(
            network_policy=network_policy, priority=priority
        )
    ]
    return self._compute_client.MakeRequests(request)

  def _MakeDeleteRuleRequestTuple(self, *, network_policy, priority):
    """Makes a request tuple for deleting a network policy rule.

    Args:
      network_policy: The name of the network policy.
      priority: The priority of the rule to delete.

    Returns:
      A tuple containing the client, method name, and request message.
    """
    return (
        self._client.regionNetworkPolicies,
        'RemoveTrafficClassificationRule',
        self._messages.ComputeRegionNetworkPoliciesRemoveTrafficClassificationRuleRequest(
            networkPolicy=network_policy,
            priority=priority,
            project=self.ref.project,
            region=self.ref.region,
        ),
    )

  def DescribeRule(
      self,
      network_policy,
      priority,
  ):
    """Sends request to describe a network policy rule."""
    request = [
        self._MakeDescribeRuleRequestTuple(
            network_policy=network_policy, priority=priority
        )
    ]
    return self._compute_client.MakeRequests(request)

  def _MakeDescribeRuleRequestTuple(self, *, network_policy, priority):
    return (
        self._client.regionNetworkPolicies,
        'GetTrafficClassificationRule',
        self._messages.ComputeRegionNetworkPoliciesGetTrafficClassificationRuleRequest(
            networkPolicy=network_policy,
            priority=priority,
            project=self.ref.project,
            region=self.ref.region,
        ),
    )

  def UpdateRule(
      self,
      *,
      priority,
      network_policy,
      network_policy_rule,
  ):
    """Sends request to update a network policy rule."""
    request = [
        self._MakeUpdateRuleRequestTuple(
            network_policy=network_policy,
            network_policy_rule=network_policy_rule,
            priority=priority,
        )
    ]
    return self._compute_client.MakeRequests(request)

  def _MakeUpdateRuleRequestTuple(
      self, *, network_policy, network_policy_rule, priority
  ):
    return (
        self._client.regionNetworkPolicies,
        'PatchTrafficClassificationRule',
        self._messages.ComputeRegionNetworkPoliciesPatchTrafficClassificationRuleRequest(
            networkPolicy=network_policy,
            networkPolicyTrafficClassificationRule=network_policy_rule,
            priority=priority,
            project=self.ref.project,
            region=self.ref.region,
        ),
    )
