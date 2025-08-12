# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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
"""Flags for the `compute public-delegated-prefixes` commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute import flags as compute_flags

PUBLIC_DELEGATED_PREFIX_FLAG_ARG = compute_flags.ResourceArgument(
    name='--public-delegated-prefix',
    resource_name='public delegated prefix',
    global_collection='compute.globalPublicDelegatedPrefixes',
    regional_collection='compute.publicDelegatedPrefixes',
    region_explanation=compute_flags.REGION_PROPERTY_EXPLANATION,
)


def MakePublicDelegatedPrefixesArg():
  return compute_flags.ResourceArgument(
      resource_name='public delegated prefix',
      regional_collection='compute.publicDelegatedPrefixes',
      global_collection='compute.globalPublicDelegatedPrefixes',
  )


def MakeRegionalPublicDelegatedPrefixesArg():
  return compute_flags.ResourceArgument(
      resource_name='public delegated prefix',
      regional_collection='compute.publicDelegatedPrefixes',
  )


def AddCreatePdpArgsToParser(
    parser, include_internal_subnetwork_creation_mode=False
):
  """Adds flags for public delegated prefixes create command."""
  parent_prefix_args = parser.add_mutually_exclusive_group(required=True)
  parent_prefix_args.add_argument(
      '--public-advertised-prefix',
      help=(
          'Public advertised prefix that this delegated prefix is created from.'
      ),
  )
  parent_prefix_args.add_argument(
      '--public-delegated-prefix',
      help=(
          'Regional Public delegated prefix that this delegated prefix is'
          ' created from.'
      ),
  )
  parser.add_argument(
      '--range',
      required=True,
      help=(
          'IP range from this public delegated prefix that should be '
          'delegated, in CIDR format. It must be smaller than parent public '
          'advertised prefix range.'
      ),
  )
  parser.add_argument(
      '--description', help='Description of this public delegated prefix.'
  )
  parser.add_argument(
      '--enable-live-migration',
      action='store_true',
      default=None,
      help=(
          'Specify if this public delegated prefix is meant to be live '
          'migrated.'
      ),
  )
  mode_choices = [
      'delegation',
      'external-ipv6-forwarding-rule-creation',
      'external-ipv6-subnetwork-creation',
  ]
  if include_internal_subnetwork_creation_mode:
    mode_choices.append('internal-ipv6-subnetwork-creation')
  base.ChoiceArgument(
      '--mode',
      choices=mode_choices,
      help_str='Specifies the mode of this IPv6 PDP.',
  ).AddToParser(parser)
  parser.add_argument(
      '--allocatable-prefix-length',
      help='The allocatable prefix length supported by this PDP.',
  )


def AddPdpPurpose(parser):
  """Adds flags for global public delegated prefixes purpose."""
  parser.add_argument(
      '--purpose',
      choices=[
          'APPLICATION_AND_PROXY_LOAD_BALANCERS',
          'PASSTHROUGH_LOAD_BALANCER_AVAILABILITY_GROUP0',
          'PASSTHROUGH_LOAD_BALANCER_AVAILABILITY_GROUP1',
      ],
      help=(
          'The purpose of the public delegated prefix. This field can only be'
          ' set for the top-level global public delegated prefix.'
      ),
  )


def _AddCommonSubPrefixArgs(parser, verb):
  """Adds common flags for delegate sub prefixes create/delete commands."""
  parser.add_argument(
      'name', help='Name of the delegated sub prefix to {}.'.format(verb)
  )
  PUBLIC_DELEGATED_PREFIX_FLAG_ARG.AddArgument(
      parser, operation_type='{} the delegate sub prefix for'.format(verb)
  )


def AddCreateSubPrefixArgs(
    parser, include_internal_subnetwork_creation_mode=False
):
  """Adds flags for delegate sub prefixes create command."""
  _AddCommonSubPrefixArgs(parser, 'create')
  parser.add_argument(
      '--range',
      help=(
          'IPv4 range from this public delegated prefix that should be '
          'delegated, in CIDR format. If not specified, the entire range of'
          'the public advertised prefix is delegated.'
      ),
  )
  parser.add_argument(
      '--description', help='Description of the delegated sub prefix to create.'
  )
  parser.add_argument(
      '--delegatee-project',
      help=(
          'Project to delegate the IPv4 range specified in `--range` to. '
          'If empty, the sub-range is delegated to the same/existing project.'
      ),
  )
  parser.add_argument(
      '--create-addresses',
      action='store_true',
      help=(
          'Specify if the sub prefix is delegated to create address '
          'resources in the delegatee project. Default is false.'
      ),
  )
  mode_choices = [
      'delegation',
      'external-ipv6-forwarding-rule-creation',
      'external-ipv6-subnetwork-creation',
  ]
  if include_internal_subnetwork_creation_mode:
    mode_choices.append('internal-ipv6-subnetwork-creation')
  base.ChoiceArgument(
      '--mode',
      choices=mode_choices,
      help_str='Specifies the mode of this IPv6 PDP.',
  ).AddToParser(parser)
  parser.add_argument(
      '--allocatable-prefix-length',
      help='Specify allocatable prefix length supported by this sub prefix.',
  )


def AddDeleteSubPrefixArgs(parser):
  """Adds flags for delegate sub prefixes delete command."""
  _AddCommonSubPrefixArgs(parser, 'delete')


def AddUpdatePrefixArgs(parser):
  parser.add_argument(
      '--announce-prefix',
      action='store_true',
      default=False,
      help='Specify if the prefix will be announced. Default is false.',
  )
  parser.add_argument(
      '--withdraw-prefix',
      action='store_true',
      default=False,
      help='Specify if the prefix will be withdrawn. Default is false.',
  )
