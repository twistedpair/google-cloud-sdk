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
"""Custom parser for ops agents."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers


# TODO(b/159913205): Migrate to calliope native solution once that feature
# request is fulfilled.
class ArgEnum(object):
  """Interpret an argument value as an item from an allowed value list.

  Example usage:

    from googlecloudsdk.api_lib.compute.instances.ops_agents.parsers import
      arg_parsers as ops_arg_parsers

    parser.add_argument(
      '--agents',
      metavar='KEY=VALUE',
      action='store',
      required=True,
      type=arg_parsers.ArgList(
          custom_delim_char=';',
          element_type=arg_parsers.ArgDict(spec={
              'type': ops_arg_parsers.ArgEnum('type', [
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
      field_name: str.
        The name of field that contains this arg value.
      allowed_values: list of allowed values.
        The allowed values to validate against.
    """
    self._field_name = field_name
    self._allowed_values = allowed_values

  def __call__(self, arg_value):
    """Interpret the arg value as an item from an allowed value list.

    Args:
      arg_value: str.
        The value of the user input argument.

    Raises:
      arg_parsers.ArgumentTypeError.
        If the arg value is not one of the allowed values.
    Returns:
      The value of the arg.
    """
    str_value = str(arg_value)
    if str_value not in self._allowed_values:
      raise arg_parsers.ArgumentTypeError(
          'Invalid value [{0}] from field [{1}], expected one of [{2}].'.format(
              arg_value, self._field_name, ', '.join(self._allowed_values)))
    return str_value
