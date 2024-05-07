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
"""Util for cloud ops agents policy commands."""

import json

from googlecloudsdk.api_lib.compute.instances.ops_agents import cloud_ops_agents_exceptions as exceptions
from googlecloudsdk.api_lib.compute.instances.ops_agents import cloud_ops_agents_policy


def GetAgentsRuleFromDescription(
    description: str,
) -> cloud_ops_agents_policy.OpsAgentsPolicy.AgentsRule | None:
  """Returns an agents rule from a OSPolicy description."""
  if description is None:
    return None
  description_parts = description.split(' | ', maxsplit=1)
  if len(description_parts) < 2:
    return None
  try:
    agents_rule_json = json.loads(description_parts[1])
  except json.JSONDecodeError:
    return None
  try:
    return cloud_ops_agents_policy.CreateAgentsRule(agents_rule_json)
  except exceptions.PolicyValidationError:
    return None
