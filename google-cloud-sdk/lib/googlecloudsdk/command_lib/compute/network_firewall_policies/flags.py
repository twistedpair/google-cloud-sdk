# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Flags and helpers for the compute network firewall policies commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.compute import completers as compute_completers
from googlecloudsdk.command_lib.compute import flags as compute_flags


DEFAULT_LIST_FORMAT = """\
    table(
      name:label=NAME,
      description
    )"""


class NetworkFirewallPoliciesCompleter(compute_completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(NetworkFirewallPoliciesCompleter, self).__init__(
        collection='compute.networkFirewallPolicies',
        list_command='compute network-firewall-policies list --uri',
        **kwargs)


def NetworkFirewallPolicyArgument(required=False, plural=False, operation=None):
  return compute_flags.ResourceArgument(
      name='FIREWALL_POLICY',
      resource_name='firewall policy',
      completer=NetworkFirewallPoliciesCompleter,
      plural=plural,
      required=required,
      custom_plural='firewall policies',
      short_help='name of the network firewall policy to {0}.'.format(
          operation),
      global_collection='compute.networkFirewallPolicies')


def AddArgNetworkFirewallPolicyCreation(parser):
  """Adds the arguments for network firewall policy creaton."""
  parser.add_argument(
      '--description',
      help=('An optional, textual description for the network firewall'
            ' policy.'))
  parser.add_argument(
      '--project',
      help=('Project in which network firewall policies is to be created'))


def AddArgsListNetworkFirewallPolicy(parser):
  """Adds the arguments for firewall policy list."""
  parser.add_argument(
      '--project',
      help=('Project to list network firewall policies from'))


def AddArgsUpdateNetworkFirewallPolicy(parser):
  """Adds the arguments  for firewall policy update."""
  parser.add_argument(
      '--project',
      help=('Project in which the network firewall policy is to be updated.'))
  parser.add_argument(
      '--description',
      help=('An optional, textual description for the network firewall'
            ' policy.'))


def NetworkFirewallPolicyAssociationArgument(required=False, plural=False,
                                             operation=None):
  return compute_flags.ResourceArgument(
      name='--name',
      resource_name='association',
      plural=plural,
      required=required,
      global_collection='compute.networkFirewallPolicies',
      short_help='name of the firewall policy association to {0}.'.format(
          operation)
      )


def AddArgsCreateAssociation(parser):
  """Adds the arguments of association creation."""
  parser.add_argument(
      '--firewall-policy',
      required=True,
      help=('Security policy ID of the association.'))

  parser.add_argument(
      '--network',
      required=True,
      help=('name of the network with which the association is created.'))

  parser.add_argument(
      '--replace-association-on-target',
      action='store_true',
      default=False,
      required=False,
      help=(
          'By default, if you attempt to insert an association to an '
          'organization or folder resource that is already associated with a '
          'firewall policy the method will fail. If this is set, the existing '
          ' association will be deleted at the same time that the new '
          'association is created.'))


def AddArgsDeleteAssociation(parser):
  """Adds the arguments of association deletion."""
  parser.add_argument(
      '--firewall-policy',
      required=True,
      help=('Security policy ID of the association.'))


class NetworksCompleter(compute_completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(NetworksCompleter, self).__init__(
        collection='compute.networks',
        list_command='compute networks list --uri',
        **kwargs)


def NetworkArgumentForOtherResource(short_help,
                                    required=True,
                                    detailed_help=None):
  return compute_flags.ResourceArgument(
      name='--network',
      resource_name='network',
      completer=NetworksCompleter,
      plural=False,
      required=required,
      global_collection='compute.networks',
      short_help=short_help,
      detailed_help=detailed_help)
