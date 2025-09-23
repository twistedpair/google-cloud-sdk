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
        **kwargs
    )


def NetworkFirewallPolicyArgument(required=False, plural=False, operation=None):
  return compute_flags.ResourceArgument(
      name='FIREWALL_POLICY',
      resource_name='firewall policy',
      completer=NetworkFirewallPoliciesCompleter,
      plural=plural,
      required=required,
      custom_plural='firewall policies',
      short_help='name of the network firewall policy to {0}.'.format(
          operation
      ),
      global_collection='compute.networkFirewallPolicies',
      regional_collection='compute.regionNetworkFirewallPolicies',
  )


def AddArgNetworkFirewallPolicyCreation(parser):
  """Adds the arguments for network firewall policy creation."""
  parser.add_argument(
      '--description',
      help='An optional, textual description for the network firewall policy.',
  )


def AddPolicyType(parser, additional_choices):
  """Adds policy type argument."""
  parser.add_argument(
      '--policy-type',
      required=False,
      choices=['VPC_POLICY', 'RDMA_ROCE_POLICY'] + additional_choices,
      help='Network firewall policy type.',
  )


def AddArgsUpdateNetworkFirewallPolicy(parser):
  """Adds the arguments  for firewall policy update."""
  parser.add_argument(
      '--description',
      help='An optional, textual description for the network firewall policy.',
  )


def NetworkFirewallPolicyAssociationArgument(
    required=False, plural=False, operation=None
):
  return compute_flags.ResourceArgument(
      name='--firewall-policy',
      resource_name='firewall policy',
      plural=plural,
      required=required,
      short_help='Firewall policy ID with which to {0} association.'.format(
          operation
      ),
      global_collection='compute.networkFirewallPolicies',
      regional_collection='compute.regionNetworkFirewallPolicies',
  )


def AddArgsCreateAssociation(
    parser,
    support_priority=False,
    support_associated_policy_to_be_replaced=False,
):
  """Adds the arguments of association creation."""
  parser.add_argument('--name', help='Name of the association.')

  parser.add_argument(
      '--network',
      required=True,
      help='Name of the network with which the association is created.',
  )

  if support_priority:
    parser.add_argument(
        '--priority',
        required=False,
        hidden=True,
        help='Priority of the association.',
    )

  group = parser
  if support_associated_policy_to_be_replaced:
    group = parser.add_group(mutex=True, required=False)
    group.add_argument(
        '--associated-policy-to-be-replaced',
        required=False,
        hidden=True,
        help='Name of an already associated firewall policy to replace.',
    )

  group.add_argument(
      '--replace-association-on-target',
      action='store_true',
      default=False,
      required=False,
      help=(
          'By default, if you attempt to insert an association to a '
          'network that is already associated with a '
          'firewall policy the method will fail. If this is set, the existing '
          'association will be deleted at the same time that the new '
          'association is created.'
      ),
  )


def AddArgsUpdateAssociation(parser):
  """Adds the arguments of association update."""
  parser.add_argument('--name', required=True, help='Name of the association.')

  parser.add_argument(
      '--priority', required=True, help='Priority of the association.'
  )


def AddArgsDeleteAssociation(parser):
  """Adds the arguments of association deletion."""
  parser.add_argument(
      '--name', required=True, help='Name of the association to delete.'
  )


class NetworksCompleter(compute_completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(NetworksCompleter, self).__init__(
        collection='compute.networks',
        list_command='compute networks list --uri',
        **kwargs
    )


def NetworkArgumentForOtherResource(
    short_help, required=True, detailed_help=None
):
  return compute_flags.ResourceArgument(
      name='--network',
      resource_name='network',
      completer=NetworksCompleter,
      plural=False,
      required=required,
      global_collection='compute.networks',
      short_help=short_help,
      detailed_help=detailed_help,
  )


def NetworkFirewallPolicyRuleArgument(
    required=False, plural=False, operation=None
):
  return compute_flags.ResourceArgument(
      name='--firewall-policy',
      resource_name='firewall policy',
      plural=plural,
      required=required,
      short_help='Firewall policy ID with which to {0} rule.'.format(operation),
      global_collection='compute.networkFirewallPolicies',
      regional_collection='compute.regionNetworkFirewallPolicies',
  )


def NetworkFirewallPolicyPacketMirroringRuleArgument(
    required=False, plural=False, operation=None
):
  return compute_flags.ResourceArgument(
      name='--firewall-policy',
      resource_name='firewall policy',
      plural=plural,
      required=required,
      short_help='Firewall policy ID with which to {0} rule.'.format(operation),
      global_collection='compute.networkFirewallPolicies',
  )


def NetworkSrcFirewallPolicyRuleArgument(required=False, plural=False):
  return compute_flags.ResourceArgument(
      name='--source-firewall-policy',
      resource_name='firewall policy',
      plural=plural,
      required=required,
      short_help='Source Firewall policy NAME with which to clone rule.',
      global_collection='compute.networkFirewallPolicies',
      regional_collection='compute.regionNetworkFirewallPolicies',
  )


def AddAction(parser, required=True):
  """Adds the action argument to the argparse."""
  parser.add_argument(
      '--action',
      choices=['allow', 'deny', 'goto_next', 'apply_security_profile_group'],
      type=lambda x: x.lower(),
      required=required,
      help='Action to take if the request matches the match condition.',
  )


def AddPacketMirroringAction(parser, required=True):
  """Adds the action argument to the argparse."""
  parser.add_argument(
      '--action',
      choices=['mirror', 'do_not_mirror', 'goto_next'],
      type=lambda x: x.lower(),
      required=required,
      help='Action to take if the request matches the match condition.',
  )


def AddRulePriority(parser, operation=None):
  """Adds the rule priority argument to the argparse."""
  parser.add_argument(
      'priority',
      help='Priority of the rule to be {}. Valid in [0, 2147483547].'.format(
          operation
      ),
  )


def AddSrcIpRanges(parser, required=False):
  """Adds the source IP ranges."""
  parser.add_argument(
      '--src-ip-ranges',
      type=arg_parsers.ArgList(),
      required=required,
      metavar='SRC_IP_RANGE',
      help=(
          'A list of IP address blocks that are allowed to make '
          'inbound connections that match the firewall rule to the instances '
          'on the network. The IP address blocks must be specified in CIDR '
          'format: http://en.wikipedia.org/wiki/Classless_Inter-Domain_Routing.'
          'Either --src-ip-ranges or --src-secure-tags must be specified for '
          'INGRESS traffic. If both --src-ip-ranges and --src-secure-tags are '
          'specified, the rule matches if either the range of the source '
          'matches --src-ip-ranges or the secure tag of the source matches '
          '--src-secure-tags.'
          'Multiple IP address blocks can be specified if they are separated '
          'by commas.'
      ),
  )


def AddDestIpRanges(parser, required=False):
  """Adds the destination IP ranges."""
  parser.add_argument(
      '--dest-ip-ranges',
      type=arg_parsers.ArgList(),
      required=required,
      metavar='DEST_IP_RANGE',
      help='Destination IP ranges to match for this rule. ',
  )


def AddLayer4Configs(parser, required=False):
  """Adds the layer4 configs."""
  parser.add_argument(
      '--layer4-configs',
      type=arg_parsers.ArgList(),
      required=required,
      metavar='LAYER4_CONFIG',
      help=(
          'A list of destination protocols and ports to which the firewall '
          'rule will apply.'
      ),
  )


def AddDirection(parser, required=False):
  """Adds the direction of the traffic to which the rule is applied."""
  parser.add_argument(
      '--direction',
      required=required,
      choices=['INGRESS', 'EGRESS'],
      help=(
          'Direction of the traffic the rule is applied. The default is to'
          ' apply on incoming traffic.'
      ),
  )


def AddEnableLogging(parser, required=False):
  """Adds the option to enable logging."""
  parser.add_argument(
      '--enable-logging',
      required=required,
      action=arg_parsers.StoreTrueFalseAction,
      help=(
          'Use this flag to enable logging of connections that allowed or '
          'denied by this rule.'
      ),
  )


def AddDisabled(parser, required=False):
  """Adds the option to disable the rule."""
  parser.add_argument(
      '--disabled',
      required=required,
      action=arg_parsers.StoreTrueFalseAction,
      help=(
          'Use this flag to disable the rule. Disabled rules will not affect '
          'traffic.'
      ),
  )


def AddGlobalFirewallPolicy(parser):
  """Adds the --global-firewall-policy flag."""
  # packet mirroring rules which currently do not support regional resources.
  # and hence this flag is not generated by default. We add it here manually so
  # that when regional firewall policies support packet mirroring rule we will
  # just replace it with the standard mechanism that genereates flags for global
  # and regional resources.
  parser.add_argument(
      '--global-firewall-policy',
      required=True,
      action='store_true',
      help='Use this flag to indicate that firewall policy is global.',
  )


def AddTargetServiceAccounts(parser, required=False):
  """Adds the target service accounts for the rule."""
  parser.add_argument(
      '--target-service-accounts',
      type=arg_parsers.ArgList(),
      metavar='TARGET_SERVICE_ACCOUNTS',
      required=required,
      help='List of target service accounts for the rule.',
  )


def AddDescription(parser, required=False):
  """Adds the description of this rule."""
  parser.add_argument(
      '--description',
      required=required,
      help='An optional, textual description for the rule.',
  )


def AddSrcSecureTags(parser, required=False, support_network_scopes=False):
  """Adds a  source secure tag to this rule."""
  help_text = (
      'A list of instance secure tags indicating the set of instances on the'
      ' network to which the rule applies if all other fields match. Either'
      ' --src-ip-ranges or --src-secure-tags must be specified for ingress'
      ' traffic. If both --src-ip-ranges and --src-secure-tags are specified,'
      ' an inbound connection is allowed if either the range of the source'
      ' matches --src-ip-ranges or the tag of the source matches'
      ' --src-secure-tags. Secure Tags can be assigned to instances during'
      ' instance creation.'
  )
  if support_network_scopes:
    help_text += (
        ' Secure tags cannot be specified if source network type is INTERNET.'
    )

  parser.add_argument(
      '--src-secure-tags',
      type=arg_parsers.ArgList(),
      metavar='SOURCE_SECURE_TAGS',
      required=required,
      help=help_text,
  )


def AddTargetSecureTags(parser, required=False):
  """Adds a target secure tag to this rule."""
  parser.add_argument(
      '--target-secure-tags',
      type=arg_parsers.ArgList(),
      metavar='TARGET_SECURE_TAGS',
      required=required,
      help=(
          'An optional, list of target secure tags with a name of the '
          'format tagValues/ or full namespaced name'
      ),
  )


def AddNewPriority(parser, operation=None):
  """Adds the new firewall policy rule priority to the argparse."""
  parser.add_argument(
      '--new-priority',
      help=(
          'New priority for the rule to {}. Valid in [0, 65535]. '.format(
              operation
          )
      ),
  )


def AddArgsCloneRules(parser):
  """Adds the argument for network firewall policy clone rules."""
  parser.add_argument(
      '--source-firewall-policy',
      required=True,
      help='Name of the source network firewall policy to copy the rules from.',
  )


def AddSrcAddressGroups(parser):
  """Adds a source address group to this rule."""
  parser.add_argument(
      '--src-address-groups',
      type=arg_parsers.ArgList(),
      metavar='SOURCE_ADDRESS_GROUPS',
      required=False,
      help=(
          'Source address groups to match for this rule. '
          'Can only be specified if DIRECTION is ingress.'
      ),
  )


def AddDestAddressGroups(parser):
  """Adds a destination address group to this rule."""
  parser.add_argument(
      '--dest-address-groups',
      type=arg_parsers.ArgList(),
      metavar='DEST_ADDRESS_GROUPS',
      required=False,
      help=(
          'Destination address groups to match for this rule. '
          'Can only be specified if DIRECTION is engress.'
      ),
  )


def AddSrcFqdns(parser):
  """Adds source fqdns to this rule."""
  parser.add_argument(
      '--src-fqdns',
      type=arg_parsers.ArgList(),
      metavar='SOURCE_FQDNS',
      required=False,
      help=(
          'Source FQDNs to match for this rule. '
          'Can only be specified if DIRECTION is `ingress`.'
      ),
  )


def AddDestFqdns(parser):
  """Adds destination fqdns to this rule."""
  parser.add_argument(
      '--dest-fqdns',
      type=arg_parsers.ArgList(),
      metavar='DEST_FQDNS',
      required=False,
      help=(
          'Destination FQDNs to match for this rule. '
          'Can only be specified if DIRECTION is `egress`.'
      ),
  )


def AddSrcRegionCodes(parser, support_network_scopes=False):
  """Adds a source region code to this rule."""
  help_text = (
      'Source Region Code to match for this rule. Can only be specified if'
      ' DIRECTION is `ingress`.'
  )
  if support_network_scopes:
    help_text += (
        ' Cannot be specified when the source network'
        ' type is NON_INTERNET, VPC_NETWORK or INTRA_VPC.'
    )
  parser.add_argument(
      '--src-region-codes',
      type=arg_parsers.ArgList(),
      metavar='SOURCE_REGION_CODES',
      required=False,
      help=help_text,
  )


def AddDestRegionCodes(parser, support_network_scopes=False):
  """Adds a destination region code to this rule."""
  help_text = (
      'Destination Region Code to match for this rule. Can only be specified if'
      ' DIRECTION is `egress`.'
  )
  if support_network_scopes:
    help_text += (
        ' Cannot be specified when the source network type is NON_INTERNET.'
    )
  parser.add_argument(
      '--dest-region-codes',
      type=arg_parsers.ArgList(),
      metavar='DEST_REGION_CODES',
      required=False,
      help=help_text,
  )


def AddSrcThreatIntelligence(parser, support_network_scopes=False):
  """Adds source threat intelligence list names to this rule."""
  help_text = (
      'Source Threat Intelligence lists to match for this rule. '
      'Can only be specified if DIRECTION is `ingress`. '
      'The available lists can be found here: '
      'https://cloud.google.com/vpc/docs/firewall-policies-rule-details#threat-intelligence-fw-policy.'
  )
  if support_network_scopes:
    help_text = (
        'Source Threat Intelligence lists to match for this rule. '
        'Can only be specified if DIRECTION is `ingress`. Cannot be specified'
        ' when the source network type is NON_INTERNET, VPC_NETWORK or'
        ' INTRA_VPC. '
        'The available lists can be found here: '
        'https://cloud.google.com/vpc/docs/firewall-policies-rule-details#threat-intelligence-fw-policy.'
    )

  parser.add_argument(
      '--src-threat-intelligence',
      type=arg_parsers.ArgList(),
      metavar='SOURCE_THREAT_INTELLIGENCE_LISTS',
      required=False,
      help=help_text,
  )


def AddDestThreatIntelligence(parser, support_network_scopes=False):
  """Adds destination threat intelligence list names to this rule."""
  help_text = (
      'Destination Threat Intelligence lists to match for this rule. '
      'Can only be specified if DIRECTION is `egress`. '
      'The available lists can be found here: '
      'https://cloud.google.com/vpc/docs/firewall-policies-rule-details#threat-intelligence-fw-policy.'
  )
  if support_network_scopes:
    help_text = (
        'Destination Threat Intelligence lists to match for this rule. '
        'Can only be specified if DIRECTION is `egress`. Cannot be specified'
        ' when source network type is NON_INTERNET.'
        ' The available lists can be found here: '
        'https://cloud.google.com/vpc/docs/firewall-policies-rule-details#threat-intelligence-fw-policy.'
    )
  parser.add_argument(
      '--dest-threat-intelligence',
      type=arg_parsers.ArgList(),
      metavar='DEST_THREAT_INTELLIGENCE_LISTS',
      required=False,
      help=help_text,
  )


def AddSecurityProfileGroup(parser):
  """Adds security profile group to this rule."""
  parser.add_argument(
      '--security-profile-group',
      metavar='SECURITY_PROFILE_GROUP',
      required=False,
      help=(
          'A security profile group to be used with'
          ' apply_security_profile_group action.'
      ),
  )


def AddMirroringSecurityProfileGroup(parser):
  """Adds security profile group to this rule."""
  parser.add_argument(
      '--security-profile-group',
      metavar='SECURITY_PROFILE_GROUP',
      required=False,
      help='A security profile group to be used with mirror action.',
  )


def AddTlsInspect(parser):
  """Adds the option to turn on TLS decryption on the rule."""
  parser.add_argument(
      '--tls-inspect',
      required=False,
      action=arg_parsers.StoreTrueFalseAction,
      help=(
          'Use this flag to indicate whether TLS traffic should be inspected '
          'using the TLS inspection policy when the security profile group '
          'is applied. Default: no TLS inspection.'
      ),
  )


def AddSrcNetworkScope(parser, required=False):
  """Adds source network scope to this rule."""
  parser.add_argument(
      '--src-network-scope',
      required=required,
      hidden=True,
      help=(
          'Deprecated. Use --src-network-type instead.'
          ' Use this flag to indicate that the rule should match internet,'
          ' non-internet traffic or traffic coming from the network specified'
          ' by --src-network. It applies to ingress rules. Valid values are'
          ' INTERNET, NON_INTERNET, VPC_NETWORKS and INTRA_VPC. Use empty'
          ' string to clear the field.'
      ),
  )


def AddSrcNetworkType(parser, required=False):
  """Adds source network type to this rule."""
  parser.add_argument(
      '--src-network-type',
      required=required,
      help=(
          'Use this flag to indicate that the rule should match internet,'
          ' non-internet traffic or traffic coming from the network specified'
          ' by --src-networks. It applies to ingress rules. Valid values are'
          ' INTERNET, NON_INTERNET, VPC_NETWORKS and INTRA_VPC. Use empty'
          ' string to clear the field.'
      ),
  )


def AddSrcNetworks(parser):
  """Adds source network urls list to this rule."""
  parser.add_argument(
      '--src-networks',
      type=arg_parsers.ArgList(),
      metavar='SRC_NETWORKS',
      required=False,
      help=(
          'The source VPC networks to  match for this rule.  It can only be'
          ' specified when --src-network-type is VPC_NETWORKS. It applies to '
          ' ingress rules. It accepts full or partial URLs.'
      ),
  )


def AddDestNetworkScope(parser, required=False):
  """Adds destination network scope to this rule."""
  parser.add_argument(
      '--dest-network-scope',
      required=required,
      hidden=True,
      help=(
          'Deprecated. Use --dest-network-type instead.'
          ' Use this flag to indicate that the rule should match internet or'
          ' non-internet traffic. It applies to destination traffic for egress'
          ' rules. Valid values are INTERNET and NON_INTERNET. Use'
          ' empty string to clear the field.'
      ),
  )


def AddDestNetworkType(parser, required=False):
  """Adds destination network type to this rule."""
  parser.add_argument(
      '--dest-network-type',
      required=required,
      help=(
          'Use this flag to indicate that the rule should match internet or'
          ' non-internet traffic. It applies to destination traffic for egress'
          ' rules. Valid values are INTERNET and NON_INTERNET. Use'
          ' empty string to clear the field.'
      ),
  )


def AddTargetType(parser, required=False):
  """Adds target type to this rule."""
  parser.add_argument(
      '--target-type',
      required=required,
      choices=['INSTANCES', 'INTERNAL_MANAGED_LB'],
      help=(
          'Target type of the rule. By default a rule applies to VM instances'
          ' (target-type = INSTANCES). Use INTERNAL_MANAGED_LB value to apply'
          ' the rule to load balancers.'
      ),
  )


def AddTargetForwardingRules(parser, required=False):
  """Adds target forwarding rules to this rule."""
  parser.add_argument(
      '--target-forwarding-rules',
      required=required,
      type=arg_parsers.ArgList(),
      metavar='TARGET_FORWARDING_RULES',
      help=(
          'A list of forwarding rules to which this rule applies. This field'
          ' allows you to control which load balancers get this rule. If not'
          ' specified, the rule applies to all load balancers. This field is'
          ' only applicable when --target-type is INTERNAL_MANAGED_LB. It'
          ' accepts full or partial resourceURLs.'
      ),
  )
