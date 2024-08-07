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
from typing import Iterator, List

from apitools.base.protorpclite import messages
from googlecloudsdk.api_lib.container.fleet import types
from googlecloudsdk.api_lib.container.fleet import util
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.calliope import parser_arguments
from googlecloudsdk.calliope import parser_extensions
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.container.fleet import errors
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.core import resources

# pylint: disable=invalid-name
# Follow the naming style in calliope library, use snake_case for properties,
# CamelCase for function names.

_BINAUTHZ_GKE_POLICY_REGEX = (
    'projects/([^/]+)/platforms/gke/policies/([a-zA-Z0-9_-]+)'
)

_PREREQUISITE_OPTION_ERROR_MSG = """\
Cannot specify --{opt} without --{prerequisite}.
"""


# TODO(b/312311133): Deduplicate shared code between fleet and rollout commands.
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
        help='Default cluster configurations to apply across the fleet.',
    )
    self._AddSecurityPostureConfig(default_cluster_config_group)
    self._AddBinaryAuthorizationConfig(default_cluster_config_group)
    self._AddCompliancePostureConfig(default_cluster_config_group)

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
        choices=['disabled', 'standard', 'enterprise'],
        default=None,
        help=textwrap.dedent("""\
          To apply standard security posture to clusters in the fleet,

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
        help=textwrap.dedent("""\
            To apply standard vulnerability scanning to clusters in the fleet,

              $ {command} --workload-vulnerability-scanning=standard

            """),
    )

  def _AddBinaryAuthorizationConfig(
      self, default_cluster_config_group: parser_arguments.ArgumentInterceptor
  ):
    binary_authorization_config_group = default_cluster_config_group.add_group(
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
        choices=['disabled', 'policy-bindings'],
        # Convert values to lower case before checking against the list of
        # options. This allows users to pass evaluation mode in enum form.
        type=lambda x: x.replace('_', '-').lower(),
        default=None,
        help=textwrap.dedent("""\
          Configure binary authorization mode for clusters to onboard the fleet,

            $ {command} --binauthz-evaluation-mode=policy-bindings

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
        action='append',
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
            max_length=1,
        ),
    )

  def _AddCompliancePostureConfig(
      self, default_cluster_config_group: parser_arguments.ArgumentInterceptor
  ):
    """Add compliance (posture) configuration."""
    compliance_posture_config_group = default_cluster_config_group.add_group(
        help='Compliance configuration.',
        hidden=True,
    )
    compliance_posture_config_group.add_argument(
        '--compliance',
        choices=['enabled', 'disabled'],
        default=None,
        metavar='compliance=MODE',
        help=textwrap.dedent("""\
          To enable compliance for clusters in the fleet,

            $ {command} --compliance=enabled

          To disable compliance for clusters in the fleet,

            $ {command} --compliance=disabled

            """),
    )
    compliance_posture_config_group.add_argument(
        '--compliance-standards',
        type=arg_parsers.ArgList(),
        default=None,
        metavar='compliance-standards=STANDARDS',
        help=textwrap.dedent("""\
          To configure compliance standards for clusters in the fleet supply a
          comma-delimited list:

            $ {command} --compliance-standards=standard-1,standard-2

          If this flag is supplied, it cannot be empty.
          """),
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

  def Fleet(self, existing_fleet=None) -> types.Fleet:
    """Fleet resource."""
    # TODO(b/290398654): Refactor to constructor style.
    fleet = self.messages.Fleet()
    fleet.name = util.FleetResourceName(self.Project())
    fleet.displayName = self._DisplayName()
    fleet.defaultClusterConfig = self._DefaultClusterConfig(existing_fleet)
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

  def _SecurityPostureConfig(self) -> types.SecurityPostureConfig:
    ret = self.messages.SecurityPostureConfig()
    ret.mode = self._SecurityPostureMode()
    ret.vulnerabilityMode = self._VulnerabilityModeValueValuesEnum()
    return self.TrimEmpty(ret)

  def _SecurityPostureMode(
      self,
  ) -> types.SecurityPostureConfigModeValueValuesEnum:
    """Parses --security-posture."""
    if '--security-posture' not in self.args.GetSpecifiedArgs():
      return None

    enum_type = self.messages.SecurityPostureConfig.ModeValueValuesEnum
    mapping = {
        'disabled': enum_type.DISABLED,
        'standard': enum_type.BASIC,
        'enterprise': enum_type.ENTERPRISE,
    }
    return mapping[self.args.security_posture]

  def _VulnerabilityModeValueValuesEnum(
      self,
  ) -> types.SecurityPostureConfigVulnerabilityModeValueValuesEnum:
    """Parses --workload-vulnerability-scanning."""
    if '--workload-vulnerability-scanning' not in self.args.GetSpecifiedArgs():
      return None

    enum_type = (
        self.messages.SecurityPostureConfig.VulnerabilityModeValueValuesEnum
    )
    mapping = {
        'disabled': enum_type.VULNERABILITY_DISABLED,
        'standard': enum_type.VULNERABILITY_BASIC,
        'enterprise': enum_type.VULNERABILITY_ENTERPRISE,
    }
    return mapping[self.args.workload_vulnerability_scanning]

  def _BinaryAuthorizationConfig(
      self, existing_binauthz=None
  ) -> types.BinaryAuthorizationConfig:
    """Construct binauthz config from args."""
    new_binauthz = self.messages.BinaryAuthorizationConfig()
    new_binauthz.evaluationMode = self._EvaluationMode()
    new_binauthz.policyBindings = list(self._PolicyBindings())

    # Merge new with existing binauthz config.
    if existing_binauthz is None:
      ret = new_binauthz
    else:
      ret = existing_binauthz
      if new_binauthz.evaluationMode is not None:
        ret.evaluationMode = new_binauthz.evaluationMode
      if new_binauthz.policyBindings is not None:
        ret.policyBindings = new_binauthz.policyBindings

    # Policy bindings only makes sense in the context of an evaluation mode.
    if ret.policyBindings and not ret.evaluationMode:
      raise exceptions.InvalidArgumentException(
          '--binauthz-policy-bindings',
          _PREREQUISITE_OPTION_ERROR_MSG.format(
              prerequisite='binauthz-evaluation-mode',
              opt='binauthz-policy-bindings',
          ),
      )

    # If evaluation mode is set to disabled, clear policy_bindings.
    if ret.evaluationMode == (
        self.messages.BinaryAuthorizationConfig.EvaluationModeValueValuesEnum.DISABLED
    ):
      ret.policyBindings = []
    return self.TrimEmpty(ret)

  def _EvaluationMode(
      self,
  ) -> types.BinaryAuthorizationConfigEvaluationModeValueValuesEnum:
    """Parses --binauthz-evaluation-mode."""
    if '--binauthz-evaluation-mode' not in self.args.GetSpecifiedArgs():
      return None

    enum_type = (
        self.messages.BinaryAuthorizationConfig.EvaluationModeValueValuesEnum
    )
    mapping = {
        'disabled': enum_type.DISABLED,
        'policy-bindings': enum_type.POLICY_BINDINGS,
    }
    return mapping[self.args.binauthz_evaluation_mode]

  def _PolicyBindings(self) -> Iterator[types.PolicyBinding]:
    """Parses --binauthz-policy-bindings."""
    policy_bindings = self.args.binauthz_policy_bindings
    if policy_bindings is not None:
      return (
          self.messages.PolicyBinding(name=binding['name'])
          for binding in policy_bindings
      )
    return []

  def _CompliancePostureConfig(
      self, existing_cfg: types.CompliancePostureConfig = None
  ) -> types.CompliancePostureConfig:
    """Construct compliance (posture) config from args."""
    cfg = (
        existing_cfg
        if existing_cfg is not None
        else self.messages.CompliancePostureConfig()
    )

    # Short circuit if no compliance flags are set.
    if self.args.compliance is None and self.args.compliance_standards is None:
      return self.TrimEmpty(cfg)

    # Determine user desired compliance mode.
    if self.args.compliance is not None:
      if self.args.compliance not in {'enabled', 'disabled'}:
        raise errors.InvalidComplianceMode(self.args.compliance)

      if (
          self.args.compliance == 'disabled'
          and self.args.compliance_standards is not None
      ):
        raise errors.ConfiguringDisabledCompliance(
            'Cannot configure compliance standards when disabling Compliance.'
        )

      if self.args.compliance == 'enabled':
        cfg.mode = (
            self.messages.CompliancePostureConfig.ModeValueValuesEnum.ENABLED
        )
      elif self.args.compliance == 'disabled':
        cfg.mode = (
            self.messages.CompliancePostureConfig.ModeValueValuesEnum.DISABLED
        )

    # Check configuration landed in a valid compliance mode state.
    if cfg.mode is None:
      raise errors.ConfiguringMissingCompliance(
          'Cannot configure compliance standards without a mode first being'
          ' set.'
      )

    # Determine user desired compliance standards.
    if self.args.compliance_standards is not None:
      desired_standards = [
          self.messages.ComplianceStandard(standard=s)
          for s in self.args.compliance_standards
      ]
      if not desired_standards:
        raise errors.ConfiguringMissingCompliance(
            '--compliance-standards must be a non-empty comma-delimited list.'
        )
      cfg.complianceStandards = desired_standards

    return self.TrimEmpty(cfg)

  def _DefaultClusterConfig(
      self,
      existing_fleet_cfg=None,
  ) -> types.DefaultClusterConfig:
    """Construct default cluster config from args.

    Args:
      existing_fleet_cfg: proto message of any currently existing configuration.

    Returns:
      Proto message for the default cluster configuration.
    """
    existing_default_cluster_config = (
        existing_fleet_cfg.defaultClusterConfig
        if existing_fleet_cfg is not None
        else None
    )
    ret = self.messages.DefaultClusterConfig()
    ret.securityPostureConfig = self._SecurityPostureConfig()
    if existing_default_cluster_config is not None:
      ret.binaryAuthorizationConfig = self._BinaryAuthorizationConfig(
          existing_default_cluster_config.binaryAuthorizationConfig
      )
    else:
      ret.binaryAuthorizationConfig = self._BinaryAuthorizationConfig()

    if existing_default_cluster_config is not None:
      ret.compliancePostureConfig = self._CompliancePostureConfig(
          existing_default_cluster_config.compliancePostureConfig
      )
    else:
      ret.compliancePostureConfig = self._CompliancePostureConfig()

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
