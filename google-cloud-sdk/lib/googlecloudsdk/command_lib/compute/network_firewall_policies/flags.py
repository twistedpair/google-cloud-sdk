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

from googlecloudsdk.calliope import arg_parsers
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
      global_collection='compute.networkFirewallPolicies',
      regional_collection='compute.regionNetworkFirewallPolicies')


def AddArgNetworkFirewallPolicyCreation(parser):
  """Adds the arguments for network firewall policy creation."""
  parser.add_argument(
      '--description',
      help=('An optional, textual description for the network firewall'
            ' policy.'))


def AddArgsUpdateNetworkFirewallPolicy(parser):
  """Adds the arguments  for firewall policy update."""
  parser.add_argument(
      '--description',
      help=('An optional, textual description for the network firewall'
            ' policy.'))


def NetworkFirewallPolicyAssociationArgument(required=False,
                                             plural=False,
                                             operation=None):
  return compute_flags.ResourceArgument(
      name='--firewall-policy',
      resource_name='firewall policy',
      plural=plural,
      required=required,
      short_help='Firewall policy ID with which to {0} association.'.format(
          operation),
      global_collection='compute.networkFirewallPolicies',
      regional_collection='compute.regionNetworkFirewallPolicies')


def AddArgsCreateAssociation(parser):
  """Adds the arguments of association creation."""
  parser.add_argument(
      '--name', help=('Name of the association.'))

  parser.add_argument(
      '--network',
      required=True,
      help=('Name of the network with which the association is created.'))

  parser.add_argument(
      '--replace-association-on-target',
      action='store_true',
      default=False,
      required=False,
      help=(
          'By default, if you attempt to insert an association to a '
          'network that is already associated with a '
          'firewall policy the method will fail. If this is set, the existing '
          'association will be deleted at the same time that the new '
          'association is created.'))


def AddArgsDeleteAssociation(parser):
  """Adds the arguments of association deletion."""
  parser.add_argument(
      '--name', required=True, help=('Name of the association to delete.'))


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


def NetworkFirewallPolicyRuleArgument(required=False,
                                      plural=False,
                                      operation=None):
  return compute_flags.ResourceArgument(
      name='--firewall-policy',
      resource_name='firewall policy',
      plural=plural,
      required=required,
      short_help='Firewall policy ID with which to {0} rule.'.format(operation),
      global_collection='compute.networkFirewallPolicies',
      regional_collection='compute.regionNetworkFirewallPolicies')


def NetworkSrcFirewallPolicyRuleArgument(required=False,
                                         plural=False):
  return compute_flags.ResourceArgument(
      name='--source-firewall-policy',
      resource_name='firewall policy',
      plural=plural,
      required=required,
      short_help='Source Firewall policy NAME with which to clone rule.',
      global_collection='compute.networkFirewallPolicies',
      regional_collection='compute.regionNetworkFirewallPolicies')


def AddAction(parser, required=True):
  """Adds the action argument to the argparse."""
  parser.add_argument(
      '--action',
      choices=['allow', 'deny', 'goto_next'],
      type=lambda x: x.lower(),
      required=required,
      help='Action to take if the request matches the match condition.')


def AddRulePriority(parser, operation=None):
  """Adds the rule priority argument to the argparse."""
  parser.add_argument(
      'priority',
      help='Priority of the rule to be {}. Valid in [0, 65535].'.format(
          operation))


def AddSrcIpRanges(parser, required=False):
  """Adds the source IP ranges."""
  parser.add_argument(
      '--src-ip-ranges',
      type=arg_parsers.ArgList(),
      required=required,
      metavar='SRC_IP_RANGE',
      help=('Source IP ranges to match for this rule. '
            'Can only be specified if DIRECTION is ingress.'))


def AddDestIpRanges(parser, required=False):
  """Adds the destination IP ranges."""
  parser.add_argument(
      '--dest-ip-ranges',
      type=arg_parsers.ArgList(),
      required=required,
      metavar='DEST_IP_RANGE',
      help=('Destination IP ranges to match for this rule. '
            'Can only be specified if DIRECTION is egress.'))


def AddLayer4Configs(parser, required=False):
  """Adds the layer4 configs."""
  parser.add_argument(
      '--layer4-configs',
      type=arg_parsers.ArgList(),
      required=required,
      metavar='LAYER4_CONFIG',
      help=('A list of destination protocols and ports to which the firewall '
            'rule will apply.'))


def AddDirection(parser, required=False):
  """Adds the direction of the traffic to which the rule is applied."""
  parser.add_argument(
      '--direction',
      required=required,
      choices=['INGRESS', 'EGRESS'],
      help=(
          'Direction of the traffic the rule is applied. The default is to apply on incoming traffic.'
      ))


def AddEnableLogging(parser, required=False):
  """Adds the option to enable logging."""
  parser.add_argument(
      '--enable-logging',
      required=required,
      action=arg_parsers.StoreTrueFalseAction,
      help=('Use this flag to enable logging of connections that allowed or '
            'denied by this rule.'))


def AddDisabled(parser, required=False):
  """Adds the option to disable the rule."""
  parser.add_argument(
      '--disabled',
      required=required,
      action=arg_parsers.StoreTrueFalseAction,
      help=('Use this flag to disable the rule. Disabled rules will not affect '
            'traffic.'))


def AddTargetServiceAccounts(parser, required=False):
  """Adds the target service accounts for the rule."""
  parser.add_argument(
      '--target-service-accounts',
      type=arg_parsers.ArgList(),
      metavar='TARGET_SERVICE_ACCOUNTS',
      required=required,
      help=('List of target service accounts for the rule.'))


def AddDescription(parser, required=False):
  """Adds the description of this rule."""
  parser.add_argument(
      '--description',
      required=required,
      help=('An optional, textual description for the rule.'))


def AddSrcSecureTags(parser, required=False):
  """Adds a  source secure tag to this rule."""
  parser.add_argument(
      '--src-secure-tags',
      type=arg_parsers.ArgList(),
      metavar='SOURCE_SECURE_TAGS',
      required=required,
      help=('An optional, list of source secure tags with a name of the '
            'format tagValues/'))


def AddTargetSecureTags(parser, required=False):
  """Adds a target secure tag to this rule."""
  parser.add_argument(
      '--target-secure-tags',
      type=arg_parsers.ArgList(),
      metavar='TARGET_SECURE_TAGS',
      required=required,
      help=('An optional, list of source secure tags with a name of the '
            'format tagValues/'))


def AddNewPriority(parser, operation=None):
  """Adds the new firewall policy rule priority to the argparse."""
  parser.add_argument(
      '--new-priority',
      help=('New priority for the rule to {}. Valid in [0, 65535]. '.format(
          operation)))


def AddArgsCloneRules(parser):
  """Adds the argument for network firewall policy clone rules."""
  parser.add_argument(
      '--source-firewall-policy',
      required=True,
      help=('Name of the source network firewall policy to copy '
            'the rules from.'))
