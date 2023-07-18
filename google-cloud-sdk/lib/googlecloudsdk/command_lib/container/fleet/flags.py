# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""Functions to add flags in fleet commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import textwrap

from apitools.base.protorpclite import messages
from googlecloudsdk.api_lib.container.fleet import util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.calliope import parser_arguments
from googlecloudsdk.calliope import parser_extensions
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.generated_clients.apis.gkehub.v1alpha import gkehub_v1alpha_messages as fleet_messages


class FleetFlags:
  """Add flags to the fleet command surface."""

  def __init__(
      self,
      parser: parser_arguments.ArgumentInterceptor,
  ):
    self._parser = parser

  @property
  def parser(self):  # pylint: disable=invalid-name
    return self._parser

  def AddAsync(self):
    base.ASYNC_FLAG.AddToParser(self.parser)

  def AddDisplayName(self):
    self.parser.add_argument(
        '--display-name',
        type=str,
        help=(
            'Display name of the fleet to be created (optional). 4-30 '
            'characters, alphanumeric and [ \'"!-] only.'
        ),
    )

  def AddDefaultClusterConfig(self):
    default_cluster_config_group = self.parser.add_group(
        help='Default cluster configurations to apply across the fleet.',
    )
    self._AddSecurityPostureConfig(default_cluster_config_group)

  def _AddSecurityPostureConfig(
      self, default_cluster_config_group: parser_arguments.ArgumentInterceptor
  ):
    security_posture_config_group = default_cluster_config_group.add_group(
        help='Security posture config.',
    )
    self._AddSecurityPostureMode(security_posture_config_group)
    self._AddWorkloadVulnerabilityScanningMode(security_posture_config_group)

  def _AddSecurityPostureMode(
      self, security_posture_config_group: parser_arguments.ArgumentInterceptor
  ):
    security_posture_config_group.add_argument(
        '--security-posture',
        choices=['disabled', 'basic', 'enterprise'],
        default=None,
        help=textwrap.dedent("""\
          To apply basic security posture to the clusters of the fleet,

            $ {command} --security-posture=basic

          """),
    )

  def _AddWorkloadVulnerabilityScanningMode(
      self, security_posture_config_group: parser_arguments.ArgumentInterceptor
  ):
    security_posture_config_group.add_argument(
        '--workload-vulnerability-scanning',
        choices=['disabled', 'basic', 'enterprise'],
        default=None,
        help=textwrap.dedent("""\
            To apply basic vulnerability scanning to the clusters of the fleet,

              $ {command} --workload-vulnerability-scanning=disabled

            """),
    )


class FleetFlagParser:
  """Parse flags during fleet command runtime."""

  def __init__(
      self, args: parser_extensions.Namespace, release_track: base.ReleaseTrack
  ):
    self.args = args
    self.release_track = release_track
    self.messages = util.FleetMessageModule(self.release_track)

  def IsEmpty(self, message: messages.Message) -> bool:
    """Determines if a message is empty.

    Args:
      message: A message to check the emptiness.

    Returns:
      A bool indictating if the message is equivalent to a newly initialized
      empty message instance.
    """
    return message == type(message)()

  def TrimEmpty(self, message: messages.Message):
    """Trim empty messages to avoid cluttered request."""
    # TODO(b/289929895): Trim child fields at the parent level.
    if not self.IsEmpty(message):
      return message
    return None

  def Fleet(self) -> fleet_messages.Fleet:
    """Fleet resource."""
    # TODO(b/290398654): Refactor to constructor style.
    fleet = self.messages.Fleet()
    fleet.name = util.FleetResourceName(self.Project())
    fleet.displayName = self._DisplayName()
    fleet.defaultClusterConfig = self._DefaultClusterConfig()
    return fleet

  def _DisplayName(self) -> str:
    return self.args.display_name

  def Project(self) -> str:
    return arg_utils.GetFromNamespace(self.args, '--project', use_defaults=True)

  def Async(self) -> bool:
    """Parses --async flag.

    The internal representation of --async is set to args.async_, defined in
    calliope/base.py file.

    Returns:
      bool, True if specified, False if unspecified.
    """
    return self.args.async_

  def _SecurityPostureConfig(self) -> fleet_messages.SecurityPostureConfig:
    ret = self.messages.SecurityPostureConfig()
    ret.mode = self._SecurityPostureMode()
    ret.vulnerabilityMode = self._VulnerabilityModeValueValuesEnum()
    return self.TrimEmpty(ret)

  def _SecurityPostureMode(
      self,
  ) -> fleet_messages.SecurityPostureConfig.ModeValueValuesEnum:
    """Parses --security-posture."""
    enum_type = self.messages.SecurityPostureConfig.ModeValueValuesEnum
    mapping = {
        'disabled': enum_type.DISABLED,
        'basic': enum_type.BASIC,
        'enterprise': enum_type.ENTERPRISE,
    }
    choice = self.args.security_posture

    if choice is None:
      return None

    valid_options = ', '.join(sorted(list(mapping)))
    if choice not in mapping:
      return exceptions.InvalidArgumentException(
          '{} not valid, expect [{}]'.format(choice, valid_options)
      )

    return mapping[choice]

  def _VulnerabilityModeValueValuesEnum(
      self,
  ) -> fleet_messages.SecurityPostureConfig.VulnerabilityModeValueValuesEnum:
    """Parses --workload-vulnerability-scanning."""
    enum_type = (
        self.messages.SecurityPostureConfig.VulnerabilityModeValueValuesEnum
    )
    mapping = {
        'disabled': enum_type.VULNERABILITY_DISABLED,
        'basic': enum_type.VULNERABILITY_BASIC,
        'enterprise': enum_type.VULNERABILITY_ENTERPRISE,
    }
    choice = self.args.workload_vulnerability_scanning

    if choice is None:
      return None

    valid_options = ', '.join(sorted(list(mapping)))
    if choice not in mapping:
      return exceptions.InvalidArgumentException(
          '{} not valid, expect [{}]'.format(choice, valid_options)
      )

    return mapping[choice]

  def _DefaultClusterConfig(self) -> fleet_messages.DefaultClusterConfig:
    ret = self.messages.DefaultClusterConfig()
    ret.securityPostureConfig = self._SecurityPostureConfig()
    return self.TrimEmpty(ret)
