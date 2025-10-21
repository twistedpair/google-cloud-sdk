# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Flags and helpers for the compute network policies commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import argparse

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.compute import completers as compute_completers
from googlecloudsdk.command_lib.compute import flags as compute_flags

_RULES_PRIORITY_UPPER_LIMIT: int = 2147483647
_RESERVED_UPPER_PRIORITIES_COUNT: int = 1000
_USER_CREATED_RULES_PRIORITY_UPPER_LIMIT: int = (
    _RULES_PRIORITY_UPPER_LIMIT - _RESERVED_UPPER_PRIORITIES_COUNT
)


class NetworkPoliciesCompleter(compute_completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(NetworkPoliciesCompleter, self).__init__(
        collection='compute.regionNetworkPolicies',
        list_command='compute network-policies list --uri',
        **kwargs,
    )


def NetworkPolicyArgument(required=False, plural=False, operation=None):
  return compute_flags.ResourceArgument(
      name='NETWORK_POLICY',
      resource_name='network policy',
      completer=NetworkPoliciesCompleter,
      plural=plural,
      required=required,
      custom_plural='network policies',
      short_help='name of the network policy to {0}.'.format(operation),
      regional_collection='compute.regionNetworkPolicies',
  )


def NetworkPolicyRuleArgument(required=False, plural=False, operation=None):
  return compute_flags.ResourceArgument(
      name='--network-policy',
      resource_name='network policy',
      plural=plural,
      required=required,
      short_help=f'Network policy ID with which to {operation} rule.',
      regional_collection='compute.regionNetworkPolicies',
  )


def NetworkPolicyAssociationArgument(
    required=False, plural=False, operation=None
):
  return compute_flags.ResourceArgument(
      name='--network-policy',
      resource_name='network policy',
      plural=plural,
      required=required,
      custom_plural='network policies',
      short_help=f'Network Policy ID with which to {operation} association.',
      regional_collection='compute.regionNetworkPolicies',
  )


def AddArgNetworkPolicyCreation(parser):
  """Adds the arguments for network policy creation."""
  parser.add_argument(
      '--description',
      help='An optional, textual description for the network policy.',
  )


def AddArgsUpdateNetworkPolicy(parser: argparse.ArgumentParser) -> None:
  """Adds the arguments for network policy update."""
  parser.add_argument(
      '--description',
      help='An optional, textual description for the network policy.',
  )


def NetworkArgumentForOtherResource(short_help, required=True):
  return compute_flags.ResourceArgument(
      name='--network',
      resource_name='network',
      completer=compute_completers.NetworksCompleter,
      plural=False,
      required=required,
      global_collection='compute.networks',
      short_help=short_help,
  )


def AddArgsCreateAssociation(parser):
  """Adds the arguments for network policy association creation."""
  parser.add_argument(
      '--name',
      help="""\
      Name of the new association. If not specified, the name will be
      auto-generated.""",
  )
  parser.add_argument(
      '--network',
      required=True,
      help='Name of the network with which the association is created.',
  )


def AddArgsRemoveAssociation(parser):
  """Adds the arguments for network policy association removal."""
  parser.add_argument(
      '--name',
      required=True,
      help='Name of the association to remove.',
  )


def AddArgsDescribeAssociation(parser):
  """Adds the arguments for network policy association description."""
  parser.add_argument(
      '--name',
      required=True,
      help='Name of the association to describe.',
  )


def AddArgsAddRule(parser: argparse.ArgumentParser) -> None:
  """Adds the arguments for network policy add rules method."""
  AddDescription(parser, required=False)
  AddRulePriority(
      parser,
      operation='added',
      required=True,
  )
  AddRuleName(parser, required=False)
  AddSrcIpRanges(parser, required=False)
  AddDestIpRanges(parser, required=True)
  AddLayer4Configs(parser, required=True)
  AddTrafficClass(parser, required=True)
  AddDscpMode(parser, required=True)
  AddDscpValue(parser, required=False)
  AddDisabled(parser, required=False)
  AddTargetServiceAccounts(parser, required=False)
  AddTargetSecureTags(parser, required=False)
  AddAction(parser, required=True)


def AddAction(parser: argparse.ArgumentParser, required: bool = False) -> None:
  """Adds the action argument to the argparse."""
  parser.add_argument(
      '--action',
      choices=['apply_traffic_classification'],
      type=lambda x: x.lower(),
      required=required,
      help='Action to take if the request matches the match condition.',
  )


def AddArgsRemoveRule(parser: argparse.ArgumentParser) -> None:
  """Adds the arguments for network policy remove rules method."""
  AddRulePriority(
      parser,
      operation='removed',
      required=True,
  )


def AddArgsDescribeRule(parser: argparse.ArgumentParser) -> None:
  """Adds the arguments for network policy describe rules method."""
  AddRulePriority(
      parser,
      operation='described',
      required=True,
      upper_limit=_RULES_PRIORITY_UPPER_LIMIT,
  )


def AddArgsUpdateRule(parser: argparse.ArgumentParser) -> None:
  """Adds the arguments for network policy update rules method."""
  AddRulePriority(
      parser,
      operation='updated',
      required=True,
  )
  AddDescription(parser)
  AddDestIpRanges(parser)
  AddDisabled(parser)
  AddTrafficClass(parser, required=False)
  AddDscpMode(parser, required=False)
  AddDscpValue(parser, required=False)
  AddLayer4Configs(parser)
  AddNewPriority(parser, operation='update')
  AddSrcIpRanges(parser)
  AddTargetSecureTags(parser)
  AddTargetServiceAccounts(parser)
  AddAction(parser, required=False)


def AddNewPriority(
    parser: argparse.ArgumentParser,
    operation: str,
    upper_limit: int = _USER_CREATED_RULES_PRIORITY_UPPER_LIMIT,
) -> None:
  """Adds the new network policy rule priority argument."""
  parser.add_argument(
      '--new-priority',
      type=arg_parsers.BoundedInt(lower_bound=1, upper_bound=upper_limit),
      help=(
          f'New priority for the rule to {operation}. '
          f'Valid priority range: [1, {upper_limit}].'
      ),
  )


def AddDisabled(
    parser: argparse.ArgumentParser, required: bool = False
) -> None:
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


def AddRulePriority(
    parser: argparse.ArgumentParser,
    operation: str,
    required: bool = False,
    upper_limit: int = _USER_CREATED_RULES_PRIORITY_UPPER_LIMIT,
) -> None:
  """Adds the rule priority argument to the argparse."""
  parser.add_argument(
      '--priority',
      required=required,
      type=arg_parsers.BoundedInt(lower_bound=1, upper_bound=upper_limit),
      help=(
          f'Priority of the rule to be {operation}. '
          f'Valid in [1, {upper_limit}].'
      ),
  )


def AddDescription(
    parser: argparse.ArgumentParser, required: bool = False
) -> None:
  """Adds the description of this rule."""
  parser.add_argument(
      '--description',
      required=required,
      help='An optional, textual description for the rule.',
  )


def AddRuleName(
    parser: argparse.ArgumentParser, required: bool = False
) -> None:
  """Adds the name of this rule."""
  parser.add_argument(
      '--name',
      required=required,
      help='An optional name for the network policy rule.',
  )


def AddSrcIpRanges(
    parser: argparse.ArgumentParser, required: bool = False
) -> None:
  """Adds the source IP ranges."""
  parser.add_argument(
      '--src-ip-ranges',
      type=arg_parsers.ArgList(),
      required=required,
      metavar='SRC_IP_RANGE',
      help='CIDR IP address range.',
  )


def AddDestIpRanges(
    parser: argparse.ArgumentParser, required: bool = False
) -> None:
  """Adds the destination IP ranges."""
  parser.add_argument(
      '--dest-ip-ranges',
      type=arg_parsers.ArgList(),
      required=required,
      metavar='DEST_IP_RANGE',
      help='Destination IP ranges to match for this rule.',
  )


def AddTrafficClass(
    parser: argparse.ArgumentParser, required: bool = False
) -> None:
  """Adds the traffic class argument."""
  parser.add_argument(
      '--traffic-class',
      choices=['tc1', 'tc2', 'tc3', 'tc4', 'tc5', 'tc6'],
      type=lambda x: x.lower(),
      required=required,
      metavar='TRAFFIC_CLASS',
      help='The traffic class that be applied to matching packet.',
  )


def AddDscpMode(
    parser: argparse.ArgumentParser, required: bool = False
) -> None:
  """Adds the DSCP mode argument."""
  parser.add_argument(
      '--dscp-mode',
      choices=['auto', 'custom'],
      type=lambda x: x.lower(),
      required=required,
      metavar='DSCP_MODE',
      help=(
          'When set to AUTO, the DSCP value will be picked automatically based'
          ' on selected traffic class. Otherwise, DSCP value must be specified.'
      ),
  )


def AddDscpValue(
    parser: argparse.ArgumentParser, required: bool = False
) -> None:
  """Adds the DSCP value argument."""
  parser.add_argument(
      '--dscp-value',
      type=arg_parsers.BoundedInt(lower_bound=0, upper_bound=63),
      required=required,
      metavar='DSCP_VALUE',
      help='Custom DSCP value from 0-63 range.',
  )


def AddLayer4Configs(
    parser: argparse.ArgumentParser, required: bool = False
) -> None:
  """Adds the layer4 configs."""
  parser.add_argument(
      '--layer4-configs',
      type=arg_parsers.ArgList(),
      required=required,
      metavar='LAYER4_CONFIG',
      help=(
          'A list of destination protocols and ports to which the network'
          ' policy rule will apply.'
      ),
  )


def AddTargetServiceAccounts(
    parser: argparse.ArgumentParser, required: bool = False
) -> None:
  """Adds the target service accounts for the rule."""
  parser.add_argument(
      '--target-service-accounts',
      type=arg_parsers.ArgList(),
      metavar='TARGET_SERVICE_ACCOUNTS',
      required=required,
      help='List of target service accounts for the rule.',
  )


def AddTargetSecureTags(
    parser: argparse.ArgumentParser, required: bool = False
) -> None:
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
