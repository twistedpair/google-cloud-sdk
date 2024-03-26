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

import os
import pathlib
import string
from typing import Optional

from apitools.base.py import encoding
from googlecloudsdk.api_lib.compute.instances.ops_agents import cloud_ops_agents_policy as agent_policy
from googlecloudsdk.core import yaml
from googlecloudsdk.core.util import files
from googlecloudsdk.generated_clients.apis.osconfig.v1 import osconfig_v1_messages as osconfig


def _CreateRollout() -> osconfig.OSPolicyAssignmentRollout:
  return osconfig.OSPolicyAssignmentRollout(
      disruptionBudget=osconfig.FixedOrPercent(percent=100),
      minWaitDuration='0s',
  )


def _GetRepoSuffix(version: Optional[str]) -> str:
  if version and '.*.*' in version:
    return version.replace('.*.*', '')
  return 'all'


def _CreateOSPolicy(
    agents_rule: agent_policy.OpsAgentsPolicy.AgentsRule,
) -> osconfig.OSPolicy:
  """Creates OS Policy from Ops Agents Rule.

  Args:
    agents_rule: User inputed agents rule.

  Returns:
    osconfig.OSPolicy
  """

  template_path = pathlib.Path(os.path.abspath(__file__)).parent
  # Check to see if specific version is used.
  # TODO: b/329073427 - Update when the next major version comes out.
  is_latest = agents_rule.version == '2.*.*' or agents_rule.version == 'latest'
  installed = (
      agents_rule.package_state
      == agent_policy.OpsAgentsPolicy.AgentsRule.PackageState.INSTALLED
  )

  if installed:
    if is_latest:
      template_name = 'policy_major_version_install.yaml'
    else:
      template_name = 'policy_pin_to_version_install.yaml'
  else:
    template_name = 'policy_uninstall.yaml'

  agent_version = (
      agents_rule.version
      if installed and not is_latest
      else _GetRepoSuffix(agents_rule.version)
  )

  template = string.Template(
      files.ReadFileContents(template_path.joinpath(template_name))
  ).safe_substitute(agent_version=agent_version)

  os_policy = encoding.PyValueToMessage(osconfig.OSPolicy, yaml.load(template))

  # Description of ops_agents_policy in a single line json format.
  os_policy.description = (
      'AUTO-GENERATED VALUE, DO NOT EDIT! | %s' % agents_rule.ToJson()
  )

  return os_policy


def ConvertOpsAgentsPolicyToOSPolicyAssignment(
    name: str,
    ops_agents_policy: agent_policy.OpsAgentsPolicy,
) -> osconfig.OSPolicyAssignment:
  """Converts Ops Agent policy to OS Config guest policy."""

  os_policy = _CreateOSPolicy(agents_rule=ops_agents_policy.agents_rule)
  os_rollout = _CreateRollout()

  return osconfig.OSPolicyAssignment(
      name=name,
      osPolicies=[os_policy],
      instanceFilter=ops_agents_policy.instance_filter,
      rollout=os_rollout,
      description='Cloud Ops Policy Assignment via gcloud',
  )
