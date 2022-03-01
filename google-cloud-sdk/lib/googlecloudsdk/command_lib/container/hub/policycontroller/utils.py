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

from googlecloudsdk.command_lib.container.hub.features import base
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
  return poco_hub_config
