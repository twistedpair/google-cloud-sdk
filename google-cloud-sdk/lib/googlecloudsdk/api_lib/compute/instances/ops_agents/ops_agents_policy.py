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
"""This class will store in-memory instance of ops agent policy."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import enum
import json
from googlecloudsdk.core.resource import resource_property


class OpsAgentPolicy(object):
  """An Ops Agent policy encapsulates the underlying OS Config Guest Policy."""

  class Agent(object):
    """An Ops Agent contains agent type, version, enable_autoupgrade."""

    class Type(str, enum.Enum):
      LOGGING = 'logging'
      METRICS = 'metrics'

    class PackageState(str, enum.Enum):
      INSTALLED = 'installed'
      REMOVED = 'removed'

    class Version(str, enum.Enum):
      LATEST_OF_ALL = 'latest'
      CURRENT_MAJOR = 'current-major'

    def __init__(self,
                 agent_type,
                 version=Version.CURRENT_MAJOR,
                 package_state=PackageState.INSTALLED,
                 enable_autoupgrade=True):
      """Initialize Agent instance.

      Args:
        agent_type: Type, agent type to be installed.
        version: str, agent version, e.g. 'latest', '5.5.2', '5.x.x'.
        package_state: Optional PackageState. DesiredState for the package.
        enable_autoupgrade: Optional bool. Enable autoupgrade for the package or
          not.
      """
      self.type = agent_type
      self.version = version
      self.package_state = package_state
      self.enable_autoupgrade = enable_autoupgrade

    def __eq__(self, other):
      return self.__dict__ == other.__dict__

    def __repr__(self):
      """JSON format string representation for testing."""
      return json.dumps(self, default=lambda o: o.__dict__,
                        indent=2, separators=(',', ': '), sort_keys=True)

    def ToJson(self):
      """Generate JSON with camel-cased key."""

      key_camel_cased_dict = {
          resource_property.ConvertToCamelCase(key): value
          for key, value in self.__dict__.items()
      }
      return json.dumps(key_camel_cased_dict, default=str, sort_keys=True)

  class Assignment(object):
    """The group or groups of VM instances that the policy applies to."""

    class OsType(object):
      """The criteria for selecting VM Instances by OS type."""

      class OsShortName(str, enum.Enum):
        CENTOS = 'centos'
        DEBIAN = 'debian'

        RHEL = 'rhel'
        SLES = 'sles'
        SLES_SAP = 'sles-sap'
        UBUNTU = 'ubuntu'

      def __init__(self, short_name, version):
        """Initialize OsType instance.

        Args:
          short_name: str, OS distro name, e.g. 'centos', 'debian'.
          version: str, OS version, e.g. '19.10', '7', '7.8'.
        """
        self.short_name = short_name
        self.version = version

      def __eq__(self, other):
        return self.__dict__ == other.__dict__

      def __repr__(self):
        """JSON format string representation for testing."""
        return json.dumps(self, default=lambda o: o.__dict__,
                          indent=2, separators=(',', ': '), sort_keys=True)

    def __init__(self, group_labels, zones, instances, os_types):
      """Initialize Assignment Instance.

      Args:
        group_labels: list of dict, VM group label matchers, or None.
        zones: list, VM zone matchers, or None.
        instances: list, instance name matchers, or None.
        os_types: OsType, VM OS type matchers, or None.
      """
      self.group_labels = group_labels or []
      self.zones = zones or []
      self.instances = instances or []
      self.os_types = os_types or []

    def __eq__(self, other):
      return self.__dict__ == other.__dict__

    def __repr__(self):
      """JSON format string representation for testing."""
      return json.dumps(self, default=lambda o: o.__dict__,
                        indent=2, separators=(',', ': '), sort_keys=True)

  def __init__(self,
               assignment,
               agents,
               description,
               etag=None,
               name=None,
               update_time=None,
               create_time=None):
    """Initialize an ops agent policy instance.

    Args:
      assignment: Assignment, selection criteria for applying policy to VMs.
      agents: list of Agent, the agent to be installed on VMs.
      description: str, user specified description of the policy.
      etag: Optional str, unique tag for policy, generated by the API.
      name: Optional str, user specified name of the policy.
      update_time: Optional str, update time in RFC3339 format.
      create_time: Optional str, create time in RFC3339 format.
    """
    self.assignment = assignment
    self.agents = agents
    self.description = description
    self.etag = etag
    self.id = name
    self.update_time = update_time
    self.create_time = create_time

  def __eq__(self, other):
    return self.__dict__ == other.__dict__

  def __repr__(self):
    """JSON format string representation for testing."""
    return json.dumps(self, default=lambda o: o.__dict__,
                      indent=2, separators=(',', ': '), sort_keys=True)


def CreateOpsAgentPolicy(description, agents, group_labels, os_types, zones,
                         instances):
  """Create Ops Agent Policy.

  Args:
    description: str, ops agent policy description.
    agents: list of dict, fields describing agents from the command line.
    group_labels: list of dict, VM group label matchers.
    os_types: dict, VM OS type matchers, or None.
    zones: list, VM zone matchers.
    instances: list, instance name matchers.

  Returns:
    ops agent policy.
  """
  assignment_os_types = []
  if os_types is not None:
    for os_type in os_types:
      assignment_os_types.append(
          OpsAgentPolicy.Assignment.OsType(
              OpsAgentPolicy.Assignment.OsType.OsShortName(
                  os_type['short-name']), os_type['version']))
  assignment = OpsAgentPolicy.Assignment(group_labels, zones, instances,
                                         assignment_os_types)

  ops_agents = []
  for agent in agents:
    ops_agents.append(
        OpsAgentPolicy.Agent(
            OpsAgentPolicy.Agent.Type(agent['type']),
            agent.get('version', OpsAgentPolicy.Agent.Version.CURRENT_MAJOR),
            OpsAgentPolicy.Agent.PackageState(
                agent.get('package-state',
                          OpsAgentPolicy.Agent.PackageState.INSTALLED)),
            agent.get('enable-autoupgrade', True)))
  return OpsAgentPolicy(assignment, ops_agents, description)
