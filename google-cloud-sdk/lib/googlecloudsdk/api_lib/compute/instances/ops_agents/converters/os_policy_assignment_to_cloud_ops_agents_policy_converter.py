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
"""Converter related function for Ops Agents Policy."""

from googlecloudsdk.api_lib.compute.instances.ops_agents import cloud_ops_agents_policy as agents_policy
from googlecloudsdk.api_lib.compute.instances.ops_agents import cloud_ops_agents_util as util
from googlecloudsdk.generated_clients.apis.osconfig.v1 import osconfig_v1_messages as osconfig


def ConvertOsPolicyAssignmentToCloudOpsAgentsPolicy(
    os_policy_assignment: osconfig.OSPolicyAssignment,
) -> agents_policy.OpsAgentsPolicy:
  """Converts OS Config guest policy to Ops Agents policy.

  A policy must have passed IsCloudOpsAgentsPolicy before this conversion.

  Args:
    os_policy_assignment: OS Config guest policy.

  Returns:
    Ops Agents policy.
  """

  assert len(os_policy_assignment.osPolicies) == 1
  description = os_policy_assignment.osPolicies[0].description
  agents_rule = util.GetAgentsRuleFromDescription(description)
  assert agents_rule is not None

  return agents_policy.OpsAgentsPolicy(
      policy_id=os_policy_assignment.name,
      agents_rule=agents_rule,
      instance_filter=os_policy_assignment.instanceFilter,
      update_time=os_policy_assignment.revisionCreateTime,
      rollout_state=os_policy_assignment.rolloutState,
  )
