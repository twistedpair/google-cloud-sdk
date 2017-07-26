# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Security policy."""


class SecurityPolicy(object):
  """Abstracts SecurityPolicy resource."""

  def __init__(self, ref, compute_client=None):
    self.ref = ref
    self._compute_client = compute_client

  @property
  def _client(self):
    return self._compute_client.apitools_client

  @property
  def _messages(self):
    return self._compute_client.messages

  def _MakeDeleteRequestTuple(self):
    return (self._client.securityPolicies, 'Delete',
            self._messages.ComputeSecurityPoliciesDeleteRequest(
                project=self.ref.project, securityPolicy=self.ref.Name()))

  def _MakeDescribeRequestTuple(self):
    return (self._client.securityPolicies, 'Get',
            self._messages.ComputeSecurityPoliciesGetRequest(
                project=self.ref.project, securityPolicy=self.ref.Name()))

  def _MakeCreateRequestTuple(self, description, rules):
    return (self._client.securityPolicies, 'Insert',
            self._messages.ComputeSecurityPoliciesInsertRequest(
                project=self.ref.project,
                securityPolicy=self._messages.SecurityPolicy(
                    name=self.ref.Name(), description=description,
                    rules=rules)))

  def _MakePatchRequestTuple(self, security_policy):
    return (self._client.securityPolicies, 'Patch',
            self._messages.ComputeSecurityPoliciesPatchRequest(
                project=self.ref.project,
                securityPolicy=self.ref.Name(),
                securityPolicyResource=security_policy))

  def Delete(self, only_generate_request=False):
    requests = [self._MakeDeleteRequestTuple()]
    if not only_generate_request:
      return self._compute_client.MakeRequests(requests)
    return requests

  def Describe(self, only_generate_request=False):
    requests = [self._MakeDescribeRequestTuple()]
    if not only_generate_request:
      return self._compute_client.MakeRequests(requests)
    return requests

  def Create(self, description='', rules=(), only_generate_request=False):
    requests = [self._MakeCreateRequestTuple(description, rules)]
    if not only_generate_request:
      return self._compute_client.MakeRequests(requests)
    return requests

  def Patch(self, security_policy=None, only_generate_request=False):
    requests = [self._MakePatchRequestTuple(security_policy)]
    if not only_generate_request:
      return self._compute_client.MakeRequests(requests)
    return requests
