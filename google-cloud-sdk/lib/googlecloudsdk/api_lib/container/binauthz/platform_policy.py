# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""API helpers for interacting with platform policies."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.container.binauthz import apis


class Client(object):
  """API helpers for interacting with platform policies."""

  def __init__(self, api_version=None):
    self.client = apis.GetClientInstance(api_version)
    self.messages = apis.GetMessagesModule(api_version)

  def Describe(self, policy_ref):
    """Describe a policy.

    Args:
      policy_ref: the resource name of the policy being described.

    Returns:
      The policy resource.
    """
    get_req = self.messages.BinaryauthorizationProjectsPlatformsPoliciesGetRequest(
        name=policy_ref,)
    return self.client.projects_platforms_policies.Get(get_req)

  def Update(self, policy_ref, policy):
    """Update a policy.

    Args:
      policy_ref: the resource name of the policy being updated.
      policy: the contents of the new policy.

    Returns:
      The updated policy resource.
    """
    policy.name = policy_ref
    return self.client.projects_platforms_policies.ReplacePlatformPolicy(policy)
