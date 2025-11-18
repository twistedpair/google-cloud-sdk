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

"""Utilities for MCP Servers and Tools API."""

from googlecloudsdk.core import properties

_PROJECT_RESOURCE = 'projects/{}'
_MCP_POLICY_DEFAULT = '/mcpPolicies/default'


# Returns the project resource in the format of projects/{project_id}
# for the current project.
@staticmethod
def GetProjectResource():
  """Returns the project ID for the current project."""
  project_id = GetProjectId()
  project_resource = _PROJECT_RESOURCE.format(project_id)
  return project_resource


# Returns the project ID for the current project.
@staticmethod
def GetProjectId():
  """Returns the project ID for the current project."""
  project_id = properties.VALUES.core.project.Get()
  return project_id


# Returns the format for the MCP Policy Default in the format of
# projects/{project_id}/mcpPolicies/default.
@staticmethod
def GetMcpPolicyDefault():
  """Returns the MCP Policy Default."""
  return _MCP_POLICY_DEFAULT
