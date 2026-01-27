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
"""Flags and parsers common across Config Management commands."""

import functools

from googlecloudsdk.command_lib.export import util as export_util
from googlecloudsdk.core import exceptions
from googlecloudsdk.core.console import console_io


class Parser:
  """Extract flag values on Config Management commands into API messages."""

  def __init__(self, hub_command):
    self.messages = hub_command.messages
    self.messages_v2 = hub_command.messages_v2

  def parse_config(self, path: str, *, is_fleet_default: bool):
    """Parse --config or --fleet-default-member-config into API message.

    Args:
      path: --config or --fleet-default-member-config flag value on update
        command. Accepts stdin.
      is_fleet_default: Whether path value is from
        --fleet-default-member-config.

    Returns:
      v2 ConfigManagementSpec or v1 ConfigManagementMembershipSpec: defaults
        enabled field to True.

    Raises:
      error: if legacy fields are set.
    """
    # Read from stdin to allow direct piping from the describe command. Also
    # consistent with Policy Controller. Accepts relative and absolute paths.
    # Do not need extra handling for home dir ~, which the shell can parse.
    data = console_io.ReadFromFileOrStdin(path, binary=False)
    return self.parse_config_data(data, is_fleet_default=is_fleet_default)

  def parse_config_data(self, data: str, *, is_fleet_default: bool):
    """Parse --config or --fleet-default-member-config content into API message.

    parse_config without reading from stdin again in the event that --config
    or --fleet-default-member-config needs to be read for pre-processing.

    Args:
      data: file content of --config or --fleet-default-member-config.
      is_fleet_default: Whether data value is from
        --fleet-default-member-config.

    Returns:
      v2 ConfigManagementSpec or v1 ConfigManagementMembershipSpec: defaults
        enabled field to True.

    Raises:
      error: if legacy fields are set.
    """
    # TODO(b/433355766): Verify the public documentation for configmanagement
    # fields in the Hub API before promotion to beta.
    api_msg = (self.messages.ConfigManagementMembershipSpec if is_fleet_default
               else self.messages_v2.ConfigManagementSpec)
    # TODO(b/459918638): Python unit test reading from stdin.
    cm_spec = export_util.Import(
        api_msg,
        data,
        # Do not add schema validation, which is done on the Hub server anyway.
        # Client-side schema validation would prevent each gcloud release from
        # being forward-compatible with new API fields and has a complex UX.
    )
    legacy_fields = _find_legacy_fields(cm_spec)
    if legacy_fields:
      flag = '--fleet-default-member-config' if is_fleet_default else '--config'
      raise exceptions.Error(
          f'{flag} does not support the following API schema fields:'
          f' {legacy_fields}. See --help for more details'
      )
    if cm_spec.configSync and cm_spec.configSync.enabled is None:
      cm_spec.configSync.enabled = True
    return cm_spec


def _find_legacy_fields(cm_spec) -> list[str]:
  """Return legacy fields in cm_spec.

  Args:
    cm_spec: v2 ConfigManagementSpec or v1 ConfigManagementMembershipSpec.

  Returns:
    list of strings: names of fields planned for deprecation at time of
      surface GA that are set.
  """
  # TODO(b/460840424): Remove fields from this list as they are removed or
  # unconditionally disallowed in the Hub API.
  field_paths = [
      'management',
      'configSync.metricsGcpServiceAccountEmail',
      'policyController',
      'hierarchyController',
      'binauthz',
  ]
  return [
      field_path
      for field_path in field_paths
      if functools.reduce(
          lambda obj, field: getattr(obj, field, None),
          field_path.split('.'),
          cm_spec,
      ) is not None
  ]
