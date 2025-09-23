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

from googlecloudsdk.command_lib.compute import completers as compute_completers
from googlecloudsdk.command_lib.compute import flags as compute_flags


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
