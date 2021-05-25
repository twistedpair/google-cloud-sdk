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
"""Network Firewall Policy."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


OP_COLLECTION_NAME = 'compute.globalOperations'
API_COLLECTION_NAME = 'compute.networkFirewallPolicies'


class NetworkFirewallPolicy(object):
  """Abstracts a network firewall policy resource."""

  def __init__(self, ref, compute_client=None):
    self.ref = ref
    self._compute_client = compute_client

  @property
  def _client(self):
    return self._compute_client.apitools_client

  @property
  def _messages(self):
    return self._compute_client.messages

  @property
  def _service(self):
    return self._client.networkFirewallPolicies

  def _HasProject(self, collection):
    collection_info = self._resources.GetCollectionInfo(collection,
                                                        self._version)
    return ('projects' in collection_info.path or
            'projects' in collection_info.base_url)

  def _MakeAddAssociationRequestTuple(self, association, firewall_policy,
                                      replace_existing_association):
    return (self._client.networkFirewallPolicies, 'AddAssociation',
            self._messages.ComputeNetworkFirewallPoliciesAddAssociationRequest(
                firewallPolicyAssociation=association,
                firewallPolicy=firewall_policy,
                replaceExistingAssociation=replace_existing_association,
                project=self.ref.project))

  def _MakeCreateRequestTuple(self, firewall_policy):
    return (self._client.networkFirewallPolicies, 'Insert',
            self._messages.ComputeNetworkFirewallPoliciesInsertRequest(
                firewallPolicy=firewall_policy, project=self.ref.project))

  def _MakeDeleteRequestTuple(self, firewall_policy):
    return (self._client.networkFirewallPolicies, 'Delete',
            self._messages.ComputeNetworkFirewallPoliciesDeleteRequest(
                firewallPolicy=firewall_policy, project=self.ref.project))

  def _MakeDescribeRequestTuple(self):
    return (self._client.networkFirewallPolicies, 'Get',
            self._messages.ComputeNetworkFirewallPoliciesGetRequest(
                firewallPolicy=self.ref.Name(), project=self.ref.project))

  def _MakeDeleteAssociationRequestTuple(self, firewall_policy, name):
    return (
        self._client.networkFirewallPolicies, 'RemoveAssociation',
        self._messages.ComputeNetworkFirewallPoliciesRemoveAssociationRequest(
            firewallPolicy=firewall_policy, name=name,
            project=self.ref.project))

  def _MakeListRequestTuple(self):
    return (self._client.networkFirewallPolicies, 'List',
            self._messages.ComputeNetworkFirewallPoliciesListRequest(
                project=self.ref.project))

  def _MakeUpdateRequestTuple(self, firewall_policy=None):
    """Sends request to update a network firewall policy."""
    return (self._client.networkFirewallPolicies, 'Patch',
            self._messages.ComputeNetworkFirewallPoliciesPatchRequest(
                firewallPolicy=self.ref.Name(),
                firewallPolicyResource=firewall_policy,
                project=self.ref.project))

  def Create(self, firewall_policy=None, only_generate_request=False):
    """Sends request to create a network firewall policy."""
    requests = [self._MakeCreateRequestTuple(firewall_policy=firewall_policy)]
    if not only_generate_request:
      return self._compute_client.MakeRequests(requests)
    return requests

  def Delete(self, firewall_policy=None, only_generate_request=False):
    """Sends request to delete a network firewall policy."""
    requests = [self._MakeDeleteRequestTuple(firewall_policy=firewall_policy)]
    if not only_generate_request:
      return self._compute_client.MakeRequests(requests)
    return requests

  def Describe(self, only_generate_request=False):
    """Sends request to describe a network firewall policy."""
    requests = [self._MakeDescribeRequestTuple()]
    if not only_generate_request:
      return self._compute_client.MakeRequests(requests)
    return requests

  def List(self, only_generate_request=False):
    """Sends request to list all the network firewall policies."""
    requests = [self._MakeListRequestTuple()]
    if not only_generate_request:
      return self._compute_client.MakeRequests(requests)
    return requests

  def Update(self, firewall_policy=None, only_generate_request=False):
    """Sends request to update an network firewall policy."""
    requests = [self._MakeUpdateRequestTuple(firewall_policy)]
    if not only_generate_request:
      return self._compute_client.MakeRequests(requests)
    return requests

  def AddAssociation(self,
                     association=None,
                     firewall_policy=None,
                     replace_existing_association=False,
                     only_generate_request=False):
    """Sends request to add an association."""
    requests = [
        self._MakeAddAssociationRequestTuple(association, firewall_policy,
                                             replace_existing_association)
    ]
    if not only_generate_request:
      return self._compute_client.MakeRequests(requests)
    return requests

  def DeleteAssociation(self,
                        firewall_policy=None,
                        name=None,
                        only_generate_request=False):
    """Sends request to delete an association."""
    requests = [
        self._MakeDeleteAssociationRequestTuple(firewall_policy, name)
    ]
    if not only_generate_request:
      return self._compute_client.MakeRequests(requests)
    return requests
