# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Flags and helpers for the compute routers nats rules commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import textwrap

from googlecloudsdk.command_lib.compute import flags as compute_flags

_ACTIVE_IPS_HELP_TEXT = textwrap.dedent("""\
    External IP Addresses to use for connections matching this rule.

    These must be valid reserved external IPs in the same region.""")


def _ActiveIpsArgument(required=False):
  return compute_flags.ResourceArgument(
      name='--source-nat-active-ips',
      detailed_help=_ACTIVE_IPS_HELP_TEXT,
      resource_name='address',
      regional_collection='compute.addresses',
      region_hidden=True,
      plural=True,
      required=required)


ACTIVE_IPS_ARG_CREATE = _ActiveIpsArgument(required=True)

# The arg is not required on update.
ACTIVE_IPS_ARG_UPDATE = _ActiveIpsArgument(required=False)


_DRAIN_IPS_HELP_TEXT = textwrap.dedent("""\
    External IP Addresses to drain connections on.

    These must be external IPs previously used as active IPs on this rule.
    No new connections will be established using these IPs.""")
DRAIN_IPS_ARG = compute_flags.ResourceArgument(
    name='--source-nat-drain-ips',
    detailed_help=_DRAIN_IPS_HELP_TEXT,
    resource_name='address',
    regional_collection='compute.addresses',
    region_hidden=True,
    plural=True,
    required=False)

DEFAULT_LIST_FORMAT = """\
    table(
      ruleNumber,
      match
    )"""


def AddNatNameArg(parser):
  """Adds an argument to identify the NAT to which the Rule belongs."""
  parser.add_argument(
      '--nat', help='Name of the NAT that contains the Rule', required=True)


def AddRuleNumberArg(parser, operation_type='operate on', plural=False):
  """Adds a positional argument for the Rule number."""
  help_text = 'Number that uniquely identifies the Rule{} to {}'.format(
      's' if plural else '', operation_type)
  params = {'help': help_text}
  if plural:
    params['nargs'] = '+'

  parser.add_argument('rule_number', type=int, **params)


def AddMatchArg(parser, required=False):
  """Adds common arguments for creating and updating NAT Rules."""
  parser.add_argument(
      '--match',
      help=textwrap.dedent("""\
      CEL Expression used to identify traffic to which this rule applies.
      * Supported attributes: destination.ip
      * Supported operators: ||, ==
      * Supported methods: inIpRange

      Examples of allowed Match expressions:
      * 'inIpRange(destination.ip, "203.0.113.0/24")''
      * 'destination.ip == "203.0.113.7"'
      * 'destination.ip == "203.0.113.7" || inIpRange(destination.ip, "203.0.113.16/25")'
      """),
      required=required)


def AddIpArgsForCreate(parser):
  """Adds arguments to specify source NAT IP Addresses when creating a rule."""
  ACTIVE_IPS_ARG_CREATE.AddArgument(parser, cust_metavar='IP_ADDRESS')


def AddIpArgsForUpdate(parser):
  """Adds argument to specify source NAT IP Addresses when updating a rule."""
  ACTIVE_IPS_ARG_UPDATE.AddArgument(parser, cust_metavar='IP_ADDRESS')
  drain_mutex = parser.add_mutually_exclusive_group(required=False)
  drain_mutex.add_argument(
      '--clear-source-nat-drain-ips',
      help='Clear drained IPs from the Rule',
      action='store_true',
      default=None)
  DRAIN_IPS_ARG.AddArgument(
      parser, mutex_group=drain_mutex, cust_metavar='IP_ADDRESS')
