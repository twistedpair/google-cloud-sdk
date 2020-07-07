# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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
"""Utility functions for GCE Ops Agents Policy commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.compute.instances.ops_agents import ops_agents_policy as agent_policy
from googlecloudsdk.calliope import arg_parsers


# TODO(b/159913205): Migrate to calliope native solution once that feature
# request is fulfilled.
class ArgEnum(object):
  """Interpret an argument value as an item from an allowed value list.

  Example usage:

    parser.add_argument(
      '--agents',
      metavar='KEY=VALUE',
      action='store',
      required=True,
      type=arg_parsers.ArgList(
          custom_delim_char=';',
          element_type=arg_parsers.ArgDict(spec={
              'type': ArgEnum('type', [
                  OpsAgentPolicy.Agent.Type.LOGGING,
                  OpsAgentPolicy.Agent.Type.METRICS]),
              'version': str,
              'package_state': str,
              'enable_autoupgrade': arg_parsers.ArgBoolean(),
          }),
      )
    )

  Example error:

    ERROR: (gcloud.alpha.compute.instances.ops-agents.policies.create) argument
    --agents: Invalid value [what] from field [type], expected one of [logging,
    metrics].
  """

  def __init__(self, field_name, allowed_values):
    """Constructor.

    Args:
      field_name: str. The name of field that contains this arg value.
      allowed_values: list of allowed values. The allowed values to validate
        against.
    """
    self._field_name = field_name
    self._allowed_values = allowed_values

  def __call__(self, arg_value):
    """Interpret the arg value as an item from an allowed value list.

    Args:
      arg_value: str. The value of the user input argument.

    Returns:
      The value of the arg.

    Raises:
      arg_parsers.ArgumentTypeError.
        If the arg value is not one of the allowed values.
    """
    str_value = str(arg_value)
    if str_value not in self._allowed_values:
      raise arg_parsers.ArgumentTypeError(
          'Invalid value [{0}] from field [{1}], expected one of [{2}].'.format(
              arg_value, self._field_name, ', '.join(self._allowed_values)))
    return str_value


def AddSharedArgs(parser):
  """Adds shared arguments to the given parser.

  Args:
    parser: A given parser
  """
  parser.add_argument(
      'POLICY_ID',
      type=arg_parsers.RegexpValidator(
          r'^ops-agents-.*$', 'POLICY_ID must start with [ops-agents-].'),
      help="""\
      Name of the policy.

      This name must contain only lowercase letters, numbers, and hyphens,
      start with a letter, end with a number or a letter, be between 1-63
      characters, and be unique within the project.
      """,
  )


def AddMutationArgs(parser):
  """Adds arguments for mutating commands.

  Args:
    parser: A given parser
  """
  parser.add_argument(
      '--description',
      type=str,
      help='Description of the policy.',
  )
  parser.add_argument(
      '--agents',
      metavar='KEY=VALUE',
      action='store',
      required=True,
      type=arg_parsers.ArgList(
          custom_delim_char=';',
          element_type=arg_parsers.ArgDict(
              spec={
                  'type':
                      ArgEnum('type', [
                          agent_policy.OpsAgentPolicy.Agent.Type.LOGGING,
                          agent_policy.OpsAgentPolicy.Agent.Type.METRICS
                      ]),
                  'version':
                      str,
                  'package-state':
                      ArgEnum('package-state', [
                          agent_policy.OpsAgentPolicy.Agent.PackageState
                          .INSTALLED,
                          agent_policy.OpsAgentPolicy.Agent.PackageState.REMOVED
                      ]),
                  'enable-autoupgrade':
                      arg_parsers.ArgBoolean(),
              },
              required_keys=['type']
          ),
      ),
      help="""\
      Agents to be installed.

      This contains fields of type(required) - sample:{logging, metrics}, version(default: latest) - sample:{6.0.0-1, 1.6.35-1, 1.x.x, 6.x.x}, package-state(default: installed) - sample:{installed, removed}, enable-autoupgrade(default: false) - sample:{true, false}.
      """,
  )
  parser.add_argument(
      '--os-types',
      metavar='KEY=VALUE',
      action='store',
      required=True,
      type=arg_parsers.ArgList(
          custom_delim_char=';',
          element_type=arg_parsers.ArgDict(spec={
              'short-name': ArgEnum(
                  'short-name',
                  [
                      agent_policy.OpsAgentPolicy.Assignment.OsType
                      .OsShortName.CENTOS,
                      agent_policy.OpsAgentPolicy.Assignment.OsType
                      .OsShortName.DEBIAN,
                      agent_policy.OpsAgentPolicy.Assignment.OsType
                      .OsShortName.RHEL,
                      agent_policy.OpsAgentPolicy.Assignment.OsType
                      .OsShortName.SLES,
                      agent_policy.OpsAgentPolicy.Assignment.OsType
                      .OsShortName.SLES_SAP,
                      agent_policy.OpsAgentPolicy.Assignment.OsType
                      .OsShortName.UBUNTU
                  ]),
              'version': str,
          }, required_keys=['short-name', 'version']),
      ),
      help="""\
      OS Types matcher for instances on which to create the policy.

      This contains fields of short_name(required) - sample:{centos, debian, rhel}, version(required) - sample:{6, 7.8}.
      """,
  )
  parser.add_argument(
      '--group-labels',
      metavar='KEY=VALUE',
      action='store',
      type=arg_parsers.ArgList(
          custom_delim_char=';',
          element_type=arg_parsers.ArgDict(),
      ),
      help="""\
      Group Labels matcher for instances on which to create the policy.

      This contains a list of key value pairs for the instances labels.
      """,
  )
  parser.add_argument(
      '--instances',
      metavar='INSTANCES',
      type=arg_parsers.ArgList(),
      help="""\
      Specifies on which instances to create the policy.

      This contains a list of instances, example: zones/us-central1-a/instances/test-instance-1
      """,
  )
  parser.add_argument(
      '--zones',
      metavar='ZONES',
      type=arg_parsers.ArgList(),
      help="""\
      Zones matcher for instance on which to create the policy.

      This contains a list of zones, example: us-central1-a.
      """,
  )
