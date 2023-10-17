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
from typing import List

from apitools.base.protorpclite import messages
from googlecloudsdk.api_lib.container.fleet import util
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.calliope import parser_arguments
from googlecloudsdk.calliope import parser_extensions
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.core import resources
from googlecloudsdk.generated_clients.apis.gkehub.v1alpha import gkehub_v1alpha_messages as fleet_messages

# pylint: disable=invalid-name
# Follow the naming style in calliope library, use snake_case for properties,
# CamelCase for function names.

_BINAUTHZ_GKE_POLICY_REGEX = (
    'projects/([^/]+)/platforms/gke/policies/([a-zA-Z0-9_-]+)'
)


class FleetFlags:
  """Add flags to the fleet command surface."""

  def __init__(
      self,
      parser: parser_arguments.ArgumentInterceptor,
  ):
    self._parser = parser

  @property
  def parser(self):
    return self._parser

  @property
  def command_name(self) -> List[str]:
    """Returns the command name.

    This provides information on the command track, command group, and the
    action.

    Returns:
      A list of command, for `gcloud alpha container fleet operations describe`,
      it returns `['gcloud', 'alpha', 'container', 'fleet', 'operations',
      'describe']`.
    """
    return self.parser.command_name

  @property
  def action(self) -> str:
    return self.command_name[-1]

  @property
  def release_track(self) -> base.ReleaseTrack:
    """Returns the release track from the given command name."""
    if self.command_name[1] == 'alpha':
      return base.ReleaseTrack.ALPHA
    elif self.command_name[1] == 'beta':
      return base.ReleaseTrack.BETA
    else:
      return base.ReleaseTrack.GA

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
        hidden=True,
        help='Default cluster configurations to apply across the fleet.',
    )
    self._AddSecurityPostureConfig(default_cluster_config_group)
    self._AddBinaryAuthorizationConfig(default_cluster_config_group)

  def _AddSecurityPostureConfig(
      self, default_cluster_config_group: parser_arguments.ArgumentInterceptor
  ):
    security_posture_config_group = default_cluster_config_group.add_group(
        hidden=True,
        help='Security posture config.',
    )
    self._AddSecurityPostureMode(security_posture_config_group)
    self._AddWorkloadVulnerabilityScanningMode(security_posture_config_group)

  def _AddSecurityPostureMode(
      self, security_posture_config_group: parser_arguments.ArgumentInterceptor
  ):
    security_posture_config_group.add_argument(
        '--security-posture',
        choices=['disabled', 'standard'],
        default=None,
        hidden=True,
        help=textwrap.dedent("""\
          To apply basic security posture to the clusters of the fleet,

            $ {command} --security-posture=standard

          """),
    )

  def _AddWorkloadVulnerabilityScanningMode(
      self, security_posture_config_group: parser_arguments.ArgumentInterceptor
  ):
    security_posture_config_group.add_argument(
        '--workload-vulnerability-scanning',
        choices=['disabled', 'standard', 'enterprise'],
        default=None,
        hidden=True,
        help=textwrap.dedent("""\
            To apply basic vulnerability scanning to the clusters of the fleet,

              $ {command} --workload-vulnerability-scanning=disabled

            """),
    )

  def _AddBinaryAuthorizationConfig(
      self, default_cluster_config_group: parser_arguments.ArgumentInterceptor
  ):
    binary_authorization_config_group = default_cluster_config_group.add_group(
        hidden=True,
        help='Binary Authorization config.',
    )
    self._AddBinauthzEvaluationMode(binary_authorization_config_group)
    self._AddBinauthzPolicyBindings(binary_authorization_config_group)

  def _AddBinauthzEvaluationMode(
      self,
      binary_authorization_config_group: parser_arguments.ArgumentInterceptor,
  ):
    binary_authorization_config_group.add_argument(
        '--binauthz-evaluation-mode',
        choices=['DISABLED', 'POLICY_BINDINGS'],
        default=None,
        hidden=True,
        help=textwrap.dedent("""\
          Configure binary authorization mode for clusters to onboard the fleet,

            $ {command} --binauthz-evaluation-mode=POLICY_BINDINGS

          """),
    )

  def _AddBinauthzPolicyBindings(
      self,
      binary_authorization_config_group: parser_arguments.ArgumentInterceptor,
  ):
    platform_policy_type = arg_parsers.RegexpValidator(
        _BINAUTHZ_GKE_POLICY_REGEX,
        'GKE policy resource names have the following format: '
        '`projects/{project_number}/platforms/gke/policies/{policy_id}`',
    )
    binary_authorization_config_group.add_argument(
        '--binauthz-policy-bindings',
        default=None,
        hidden=True,
        metavar='name=BINAUTHZ_POLICY',
        help=textwrap.dedent("""\
          The relative resource name of the Binary Authorization policy to audit
          and/or enforce. GKE policies have the following format:
          `projects/{project_number}/platforms/gke/policies/{policy_id}`."""),
        type=arg_parsers.ArgDict(
            spec={
                'name': platform_policy_type,
            },
            required_keys=['name'],
        ),
    )

  def _OperationResourceSpec(self):
    return concepts.ResourceSpec(
        'gkehub.projects.locations.operations',
        resource_name='operation',
        api_version=util.VERSION_MAP[self.release_track],
        locationsId=self._LocationAttributeConfig(),
        projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
    )

  def AddOperationResourceArg(self):
    concept_parsers.ConceptParser.ForResource(
        'operation',
        self._OperationResourceSpec(),
        group_help='operation to {}.'.format(self.action),
        required=True,
    ).AddToParser(self.parser)
    self.parser.set_defaults(location='global')

  def _LocationAttributeConfig(self):
    """Gets Google Cloud location resource attribute."""
    return concepts.ResourceParameterAttributeConfig(
        name='location',
        help_text='Google Cloud location for the {resource}.',
    )

  def AddLocation(self):
    self.parser.add_argument(
        '--location',
        type=str,
        help='The location name.',
        default='-',
    )


class FleetFlagParser:
  """Parse flags during fleet command runtime."""

  def __init__(
      self, args: parser_extensions.Namespace, release_track: base.ReleaseTrack
  ):
    self.args = args
    self.release_track = release_track
    self.messages = util.GetMessagesModule(release_track)

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
    if self.release_track == base.ReleaseTrack.ALPHA:
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
        'standard': enum_type.BASIC,
    }
    choice = self.args.security_posture

    if choice is None:
      return None

    valid_options = ', '.join(sorted(list(mapping)))
    if choice not in mapping:
      return exceptions.InvalidArgumentException(
          choice, 'expect [{}]'.format(valid_options)
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
        'standard': enum_type.VULNERABILITY_BASIC,
        'enterprise': enum_type.VULNERABILITY_ENTERPRISE,
    }
    choice = self.args.workload_vulnerability_scanning

    if choice is None:
      return None

    valid_options = ', '.join(sorted(list(mapping)))
    if choice not in mapping:
      return exceptions.InvalidArgumentException(
          choice, 'expect [{}]'.format(valid_options)
      )

    return mapping[choice]

  def _BinaryAuthorizationConfig(
      self) -> fleet_messages.BinaryAuthorizationConfig:
    ret = self.messages.BinaryAuthorizationConfig()
    ret.evaluationMode = self._EvaluationMode()
    ret.policyBindings = self._PolicyBindings()
    return self.TrimEmpty(ret)

  def _EvaluationMode(
      self,
  ) -> fleet_messages.BinaryAuthorizationConfig.EvaluationModeValueValuesEnum:
    """Parses --binauthz-evaluation-mode."""
    enum_type = (
        self.messages.BinaryAuthorizationConfig.EvaluationModeValueValuesEnum
    )
    mapping = {
        'DISABLED': enum_type.DISABLED,
        'POLICY_BINDINGS': enum_type.POLICY_BINDINGS,
    }
    choice = self.args.binauthz_evaluation_mode

    if choice is None:
      return None

    valid_options = ', '.join(sorted(list(mapping)))
    if choice not in mapping:
      return exceptions.InvalidArgumentException(
          choice, 'expect [{}]'.format(valid_options)
      )

    return mapping[choice]

  def _PolicyBindings(self) -> [fleet_messages.PolicyBinding]:
    """Parses --binauthz-policy-bindings."""
    policy_binding = self.args.binauthz_policy_bindings
    if policy_binding is not None:
      return [
          fleet_messages.PolicyBinding(name=policy_binding[0]['name'])
      ]
    return []

  def _DefaultClusterConfig(self) -> fleet_messages.DefaultClusterConfig:
    ret = self.messages.DefaultClusterConfig()
    ret.securityPostureConfig = self._SecurityPostureConfig()
    ret.binaryAuthorizationConfig = self._BinaryAuthorizationConfig()
    return self.TrimEmpty(ret)

  def OperationRef(self) -> resources.Resource:
    """Parses resource argument operation."""
    return self.args.CONCEPTS.operation.Parse()

  def Location(self) -> str:
    return self.args.location

  def PageSize(self) -> int:
    """Returns page size in a list request."""
    return self.args.page_size

  def Limit(self) -> int:
    """Returns limit in a list request."""
    return self.args.limit
