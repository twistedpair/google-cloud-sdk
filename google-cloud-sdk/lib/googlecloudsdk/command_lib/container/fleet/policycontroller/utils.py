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

from googlecloudsdk.command_lib.container.fleet.features import base
from googlecloudsdk.core import exceptions
from googlecloudsdk.core.console import console_io


def select_memberships(args):
  """Returns a list of memberships to which to apply the command, given the arguments.

  Args:
    args: object containing arguments passed as flags with the command

  Returns:
    memberships: A list of membership name strings
  """
  memberships = []
  all_memberships = base.ListMemberships()

  if args.all_memberships:
    memberships = all_memberships
  elif args.memberships:
    memberships = args.memberships.split(',')
    for membership in memberships:
      if membership not in all_memberships:
        raise exceptions.Error('Membership {} not found'.format(membership))
  else:
    index = console_io.PromptChoice(
        options=all_memberships, message='Please specify a membership:\n')
    memberships = [all_memberships[index]]

  if not memberships:
    raise exceptions.Error('A membership is required for this command.')

  return memberships


def set_poco_hub_config_parameters_from_args(args, messages):
  """Returns a Policy Controller Hub Config object with parameters as passed in the command flags.

  Args:
    args: object containing arguments passed as flags with the command
    messages: GKE Hub proto messages

  Returns:
    poco_hub_config: Policy Controller Hub Config object with parameters filled
    out
  """
  poco_hub_config = messages.PolicyControllerHubConfig(
    )
  merge_args_with_poco_hub_config(args, poco_hub_config, messages)
  return poco_hub_config


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
  if args.log_denies_enabled is not None:
    poco_hub_config.logDeniesEnabled = args.log_denies_enabled
  if args.referential_rules_enabled is not None:
    poco_hub_config.referentialRulesEnabled = args.referential_rules_enabled
  if args.template_library_installed is not None:
    poco_hub_config.templateLibraryConfig = messages.PolicyControllerTemplateLibraryConfig(
        included=args.template_library_installed)


class BooleanOptionalAction(argparse.Action):
  """BooleanOptionalAction is copied from Python 3.9 library.

  This is a workaround before the minimum supported version of python is updated
  to 3.9 in gcloud, or the field mask bug is implemented (b/233366392),
  whichever comes first.
  """

  def __init__(self,
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
