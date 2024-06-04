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
from typing import Optional

from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.compute.instances.ops_agents import cloud_ops_agents_exceptions as exceptions
from googlecloudsdk.api_lib.compute.instances.ops_agents import cloud_ops_agents_policy
from googlecloudsdk.api_lib.compute.instances.ops_agents.converters import os_policy_assignment_to_cloud_ops_agents_policy_converter as to_ops_agents_policy
from googlecloudsdk.api_lib.compute.instances.ops_agents.validators import cloud_ops_agents_policy_validator
from googlecloudsdk.api_lib.compute.os_config import utils as osconfig_api_utils
from googlecloudsdk.command_lib.compute.os_config import utils as osconfig_command_utils


def GetAgentsRuleFromDescription(
    description: str,
) -> Optional[cloud_ops_agents_policy.OpsAgentsPolicy.AgentsRule]:
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


def GetOpsAgentsPolicyFromApi(
    release_track: str, policy_id: str, project: str, zone: str
) -> cloud_ops_agents_policy.OpsAgentsPolicy:
  """Retrieves an Ops Agents policy from the OS Config API.

  Args:
    release_track: API release track.
    policy_id: User's POLICY_ID from command prompt.
    project: User's project.
    zone: User's zone.

  Returns:
    A validated OpsAgentsPolicy.

  Raises:
    PolicyNotFoundError: The policy_id does not exist.
    PolicyMalformedError: The policy is not an Ops Agents policy.
    PolicyValidationMultiError: The policy is not a valid Ops Agents policy.
  """
  messages = osconfig_api_utils.GetClientMessages(release_track)
  client = osconfig_api_utils.GetClientInstance(release_track)
  service = client.projects_locations_osPolicyAssignments

  parent_path = osconfig_command_utils.GetProjectLocationUriPath(project, zone)

  assignment_id = osconfig_command_utils.GetOsPolicyAssignmentRelativePath(
      parent_path, policy_id
  )

  get_request = messages.OsconfigProjectsLocationsOsPolicyAssignmentsGetRequest(
      name=assignment_id
  )
  try:
    get_response = service.Get(get_request)
  except apitools_exceptions.HttpNotFoundError:
    raise exceptions.PolicyNotFoundError(policy_id=policy_id)
  if not cloud_ops_agents_policy_validator.IsCloudOpsAgentsPolicy(get_response):
    raise exceptions.PolicyMalformedError(policy_id=policy_id)
  ops_agents_policy = (
      to_ops_agents_policy.ConvertOsPolicyAssignmentToCloudOpsAgentsPolicy(
          get_response
      )
  )
  return ops_agents_policy
