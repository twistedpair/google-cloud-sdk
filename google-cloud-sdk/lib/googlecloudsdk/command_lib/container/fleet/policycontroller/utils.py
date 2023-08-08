# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Utils for GKE Hub Policy Controller commands."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from googlecloudsdk.command_lib.projects import util
from googlecloudsdk.core import exceptions


ENFORCEMENT_ACTION_LABEL_MAP = {
    'ENFORCEMENT_ACTION_UNSPECIFIED': 'UNSPECIFIED',
    'ENFORCEMENT_ACTION_DENY': 'DENY',
    'ENFORCEMENT_ACTION_DRYRUN': 'DRYRUN',
    'ENFORCEMENT_ACTION_WARN': 'WARN',
}

INSTALL_SPEC_LABEL_MAP = {
    'INSTALL_SPEC_ENABLED': 'ENABLED',
    'INSTALL_SPEC_NOT_INSTALLED': 'NOT_INSTALLED',
    'INSTALL_SPEC_SUSPENDED': 'SUSPENDED',
    'INSTALL_SPEC_UNSPECIFIED': 'UNSPECIFIED',
}


def get_install_spec_label(install_spec):
  if install_spec in INSTALL_SPEC_LABEL_MAP:
    return INSTALL_SPEC_LABEL_MAP[install_spec]
  return INSTALL_SPEC_LABEL_MAP['INSTALL_SPEC_UNSPECIFIED']


def get_enforcement_action_label(enforcement_action):
  if enforcement_action in ENFORCEMENT_ACTION_LABEL_MAP:
    return ENFORCEMENT_ACTION_LABEL_MAP[enforcement_action]
  return ENFORCEMENT_ACTION_LABEL_MAP['ENFORCEMENT_ACTION_UNSPECIFIED']


def set_poco_hub_config_parameters_from_args(args, messages):
  """Returns a Policy Controller Hub Config object with parameters as passed in the command flags.

  Args:
    args: object containing arguments passed as flags with the command
    messages: GKE Hub proto messages

  Returns:
    poco_hub_config: Policy Controller Hub Config object with parameters filled
    out
  """
  validate_args(args)
  poco_hub_config = messages.PolicyControllerHubConfig()
  merge_args_with_poco_hub_config(args, poco_hub_config, messages)
  return poco_hub_config


# TODO(b/291816961) Validate should ultimately be removed. Hacks here to handle
# different arg namespaces are only temporary until all commands can be brought
# into line.
def validate_args(args):
  """Validates the passed in arguments to make sure no incompatible arguments are used together.

  Args:
    args: object containing arguments passed as flags with the command
  """
  if args.monitoring is not None and args.no_monitoring:
    raise exceptions.Error(
        'Both monitoring and no-monitoring cannot be used in the same command'
    )

  if (
      args.exemptable_namespaces is not None
      and args.clear_exemptable_namespaces
  ):
    raise exceptions.Error(
        'Both exemptable-namespaces and no-exemptable-namespaces '
        + 'cannot be used in the same command'
    )


def convert_membership_from_project_id_to_number(membership_path):
  """Converts the passed in membership path with project IDs to membership path with project numbers.

  Args:
    membership_path: membership path string in the form of
      projects/{project_id}/locations/{location}/memberships/{membership_id}

  Returns:
    membership_path: membership path string in the form of
      projects/{project_number}/locations/{location}/memberships/{membership_id}
  """
  splits = membership_path.split('/')
  if (
      len(splits) != 6
      or splits[0] != 'projects'
      or splits[2] != 'locations'
      or splits[4] != 'memberships'
  ):
    raise exceptions.Error(
        '{} is not a valid membership path'.format(membership_path)
    )
  project_number = util.GetProjectNumber(splits[1])
  return 'projects/{}/locations/{}/memberships/{}'.format(
      project_number, splits[3], splits[5]
  )


# TODO(b/291816961) Validate should ultimately be removed. Hacks here to handle
# different arg namespaces are only temporary until all commands can be brought
# into line.
def merge_args_with_poco_hub_config(args, poco_hub_config, messages):
  """Sets the given Policy Controller Hub Config object with parameters as passed in the command flags.

  If nothing is set in args, preserve the original config object.

  Args:
    args: object containing arguments passed as flags with the command
    poco_hub_config: current config object read from GKE Hub API
    messages: GKE Hub proto messages
  """
  if args.audit_interval:
    poco_hub_config.auditIntervalSeconds = args.audit_interval

  if args.constraint_violation_limit is not None:
    poco_hub_config.constraintViolationLimit = args.constraint_violation_limit

  if args.exemptable_namespaces:
    exemptable_namespaces = args.exemptable_namespaces.split(',')
    poco_hub_config.exemptableNamespaces = exemptable_namespaces

  if args.clear_exemptable_namespaces:
    poco_hub_config.exemptableNamespaces = []

  if args.log_denies is not None:
    poco_hub_config.logDeniesEnabled = args.log_denies

  if args.mutation is not None:
    poco_hub_config.mutationEnabled = args.mutation

  if args.referential_rules is not None:
    poco_hub_config.referentialRulesEnabled = args.referential_rules

  # Default the library to on if it is unspecified, otherwise interpret the arg.
  install_library = True
  if args.template_library is not None:
    install_library = args.template_library
  set_template_library_config(install_library, poco_hub_config, messages)

  if args.monitoring is not None:
    poco_hub_config.monitoring = build_poco_monitoring_config(
        args.monitoring.split(','), messages
    )

  if hasattr(args, 'no_monitoring') and args.no_monitoring:
    poco_hub_config.monitoring = build_poco_monitoring_config([], messages)

  if hasattr(args, 'suspend') and args.suspend is not None:
    if args.suspend:
      poco_hub_config.installSpec = (
          messages.PolicyControllerHubConfig.InstallSpecValueValuesEnum.INSTALL_SPEC_SUSPENDED
      )
    else:
      poco_hub_config.installSpec = (
          messages.PolicyControllerHubConfig.InstallSpecValueValuesEnum.INSTALL_SPEC_ENABLED
      )


def set_template_library_config(enabled, poco_hub_config, messages):
  """Sets the given Policy Controller Hub Config object's TemplateLibraryConfig.

  Args:
    enabled: boolean installation of the template library
    poco_hub_config: current config object read from GKE Hub API
    messages: GKE Hub proto messages
  """
  # Map True/False to ALL/NOT_INSTALLED
  # pylint: disable=line-too-long
  # TODO(b/275747711): Get rid of the pylint exemption and format all of this
  # automagically.
  install = (
      messages.PolicyControllerTemplateLibraryConfig.InstallationValueValuesEnum.ALL
      if enabled
      else messages.PolicyControllerTemplateLibraryConfig.InstallationValueValuesEnum.NOT_INSTALLED
  )

  library_config = messages.PolicyControllerTemplateLibraryConfig(
      installation=install
  )

  if poco_hub_config.policyContent is None:
    poco_hub_config.policyContent = messages.PolicyControllerPolicyContentSpec()
  poco_hub_config.policyContent.templateLibrary = library_config


def build_poco_monitoring_config(backends_list, messages):
  """Build the PoCo Monitoring Config message with backend string list passed in the command.

  If nothing is set in args, preserve the original config object.

  Args:
    backends_list: list of strings that will be converted to backend options
    messages: GKE Hub proto messages

  Returns:
    Policy Controller Monitoring Config message with the backends list
  """
  backends = []
  for backend in backends_list:
    if backend == 'prometheus':
      backends.append(
          messages.PolicyControllerMonitoringConfig.BackendsValueListEntryValuesEnum.PROMETHEUS
      )
    elif backend == 'cloudmonitoring':
      backends.append(
          messages.PolicyControllerMonitoringConfig.BackendsValueListEntryValuesEnum.CLOUD_MONITORING
      )
    else:
      raise exceptions.Error(
          'policycontroller.monitoring.backend '
          + backend
          + ' is not recognized'
      )
  return messages.PolicyControllerMonitoringConfig(backends=backends)
