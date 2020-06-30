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
"""Converter related function for Ops Agents Policy."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import json

from googlecloudsdk.api_lib.compute.instances.ops_agents import ops_agents_policy as agent_policy
from googlecloudsdk.calliope import exceptions


def _CreateGroupLabels(policy_group_labels):
  group_labels = []
  for policy_group_label in policy_group_labels or []:
    pairs = {
        label.key: label.value
        for label in policy_group_label.labels.additionalProperties
    }
    group_labels.append(pairs)
  return group_labels


def _ExtractDescriptionAndAgents(description):
  try:
    decode_description = json.loads(description)
  except ValueError as e:
    raise exceptions.BadArgumentException(
        'description', 'guest policy description contains invalid JSON: %s' % e)
  return (decode_description.get('description'), decode_description['agents'])


def _CreateAgents(agents):
  """Create agents in ops agent policy.

  Args:
    agents: json objects.

  Returns:
    agents in ops agent policy.
  """
  ops_agents = []

  for agent in agents or []:
    try:
      ops_agents.append(
          agent_policy.OpsAgentPolicy.Agent(agent['type'], agent['version'],
                                            agent['packageState'],
                                            agent['enableAutoupgrade']))
    except KeyError as e:
      raise exceptions.BadArgumentException(
          'description.agents',
          'agent specification %s missing a required key: %s' % (agent, e))
  return ops_agents


def _CreateAssignment(guest_policy_assignment):
  """Create assignment in ops agent policy from a guest policy assignment.

  Args:
    guest_policy_assignment: type of assignment in guest policy.

  Returns:
    assignment in ops agent policy.
  """
  os_types = []
  for guest_os_type in guest_policy_assignment.osTypes or []:
    os_type = agent_policy.OpsAgentPolicy.Assignment.OsType(
        guest_os_type.osShortName, guest_os_type.osVersion,
        guest_os_type.osArchitecture)
    os_types.append(os_type)
  assignment = agent_policy.OpsAgentPolicy.Assignment(
      _CreateGroupLabels(guest_policy_assignment.groupLabels),
      guest_policy_assignment.zones, guest_policy_assignment.instances,
      os_types)
  return assignment


def ConvertGuestPolicyToOpsAgentPolicy(guest_policy):
  description, agents = _ExtractDescriptionAndAgents(guest_policy.description)
  ops_agent_policy = agent_policy.OpsAgentPolicy(
      _CreateAssignment(guest_policy.assignment), _CreateAgents(agents),
      description, guest_policy.etag, guest_policy.name,
      guest_policy.updateTime, guest_policy.createTime)
  return ops_agent_policy
