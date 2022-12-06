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

import argparse

from googlecloudsdk.command_lib.projects import util
from googlecloudsdk.core import exceptions


ENFORCEMENT_ACTION_LABEL_MAP = {
    'ENFORCEMENT_ACTION_UNSPECIFIED': 'UNSPECIFIED',
    'ENFORCEMENT_ACTION_DENY': 'DENY',
    'ENFORCEMENT_ACTION_DRYRUN': 'DRYRUN',
    'ENFORCEMENT_ACTION_WARN': 'WARN'
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


def validate_args(args):
  """Validates the passed in arguments to make sure no incompatible arguments are used together.

  Args:
    args: object containing arguments passed as flags with the command
  """
  if args.monitoring is not None and args.no_monitoring:
    raise exceptions.Error(
        'Both monitoring and no-monitoring cannot be used in the same command')
  if args.exemptable_namespaces is not None and args.no_exemptable_namespaces:
    raise exceptions.Error(
        'Both exemptable-namespaces and no-exemptable-namespaces ' +
        'cannot be used in the same command')


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
  if len(splits) != 6 or splits[0] != 'projects' or splits[
      2] != 'locations' or splits[4] != 'memberships':
    raise exceptions.Error(
        '{} is not a valid membership path'.format(membership_path))
  project_number = util.GetProjectNumber(splits[1])
  return 'projects/{}/locations/{}/memberships/{}'.format(
      project_number, splits[3], splits[5])


def merge_args_with_poco_hub_config(args, poco_hub_config, messages):
  """Sets the given Policy Controller Hub Config object with parameters as passed in the command flags.

  If nothing is set in args, preserve the original config object.

  Args:
    args: object containing arguments passed as flags with the command
    poco_hub_config: current config object read from GKE Hub API
    messages: GKE Hub proto messages
  """
  if args.audit_interval_seconds:
    poco_hub_config.auditIntervalSeconds = args.audit_interval_seconds
  if args.exemptable_namespaces:
    exemptable_namespaces = args.exemptable_namespaces.split(',')
    poco_hub_config.exemptableNamespaces = exemptable_namespaces
  elif args.no_exemptable_namespaces:
    poco_hub_config.exemptableNamespaces = []
  if args.log_denies_enabled is not None:
    poco_hub_config.logDeniesEnabled = args.log_denies_enabled
  if hasattr(args, 'mutation_enabled') and args.mutation_enabled is not None:
    poco_hub_config.mutationEnabled = args.mutation_enabled
  if args.referential_rules_enabled is not None:
    poco_hub_config.referentialRulesEnabled = args.referential_rules_enabled
  if args.template_library_installed is not None:
    poco_hub_config.templateLibraryConfig = messages.PolicyControllerTemplateLibraryConfig(
        included=args.template_library_installed)
  if args.monitoring is not None:
    poco_hub_config.monitoring = build_poco_monitoring_config(
        args.monitoring.split(','), messages)
  if args.no_monitoring:
    poco_hub_config.monitoring = build_poco_monitoring_config([], messages)
  if hasattr(args, 'suspend') and args.suspend is not None:
    if args.suspend:
      poco_hub_config.installSpec = messages.PolicyControllerHubConfig.InstallSpecValueValuesEnum.INSTALL_SPEC_SUSPENDED
    else:
      poco_hub_config.installSpec = messages.PolicyControllerHubConfig.InstallSpecValueValuesEnum.INSTALL_SPEC_ENABLED


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
      backends.append(messages.PolicyControllerMonitoringConfig
                      .BackendsValueListEntryValuesEnum.PROMETHEUS)
    elif backend == 'cloudmonitoring':
      backends.append(messages.PolicyControllerMonitoringConfig
                      .BackendsValueListEntryValuesEnum.CLOUD_MONITORING)
    else:
      raise exceptions.Error('policycontroller.monitoring.backend ' + backend +
                             ' is not recognized')
  return messages.PolicyControllerMonitoringConfig(backends=backends)


class BooleanOptionalAction(argparse.Action):
  """BooleanOptionalAction is copied from Python 3.9 library.

  This is a workaround before the minimum supported version of python is updated
  to 3.9 in gcloud, or the field mask bug is implemented (b/233366392),
  whichever comes first.
  """

  def __init__(
      self,
      option_strings,
      dest,
      default=None,
      type=None,  # pylint: disable=redefined-builtin
      choices=None,
      required=False,
      help=None,  # pylint: disable=redefined-builtin
      metavar=None,
      const=None):

    _option_strings = []  # pylint: disable=invalid-name
    for option_string in option_strings:
      _option_strings.append(option_string)

      if option_string.startswith('--'):
        option_string = '--no-' + option_string[2:]
        _option_strings.append(option_string)

    if help is not None and default is not None:
      help += ' (default: %(default)s)'

    super(BooleanOptionalAction, self).__init__(
        option_strings=_option_strings,
        dest=dest,
        nargs=0,
        default=default,
        type=type,
        choices=choices,
        required=required,
        help=help,
        metavar=metavar,
        const=const)

  def __call__(self, parser, namespace, values, option_string=None):
    if option_string in self.option_strings:
      setattr(namespace, self.dest, not option_string.startswith('--no-'))

  def format_usage(self):
    return ' | '.join(self.option_strings)
