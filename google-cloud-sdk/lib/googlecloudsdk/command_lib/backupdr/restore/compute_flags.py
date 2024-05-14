# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Flags for backup-dr restore compute commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.backupdr import util
from googlecloudsdk.command_lib.util.concepts import concept_parsers


def AddNameArg(parser, required=True):
  parser.add_argument(
      '--name',
      type=str,
      required=required,
      help='Name of the restored Compute Instance.',
  )


def AddTargetZoneArg(parser, required=True):
  parser.add_argument(
      '--target-zone',
      type=str,
      required=required,
      help='Zone where the target instance is restored.',
  )


def AddTargetProjectArg(parser, required=True):
  name = '--target-project'
  project_spec = concepts.ResourceSpec(
      'backupdr.projects',
      resource_name='Target Project',
      disable_auto_completers=False,
  )

  concept_parsers.ConceptParser.ForResource(
      name,
      project_spec,
      'Project where the restore should happen.',
      required=required,
  ).AddToParser(parser)


def AddNetworkInterfaceArg(parser, required=True):
  """Network interface of the restored resource."""
  network_tier_options = ('NETWORK_TIER_UNSPECIFIED', 'STANDARD', 'PREMIUM')
  stack_type_options = ('STACK_TYPE_UNSPECIFIED', 'IPV4_ONLY', 'IPV4_IPV6')
  nic_type_options = ('NIC_TYPE_UNSPECIFIED', 'VIRTIO_NET', 'GVNIC')

  network_tier_validator = util.GetOneOfValidator(
      'network-tier', network_tier_options
  )
  stack_type_validator = util.GetOneOfValidator(
      'stack-type', stack_type_options
  )
  nic_type_validator = util.GetOneOfValidator('nic-type', nic_type_options)
  network_interface_spec = {
      'network': str,
      'subnet': str,
      'address': str,
      'internal-ipv6-address': str,
      'internal-ipv6-prefix-length': int,
      'external-ipaddress': str,
      'external-ipv6-address': str,
      'external-ipv6-prefix-length': int,
      'public-ptr-domain': str,
      'ipv6-public-ptr-domain': str,
      'network-tier': network_tier_validator,
      'aliases': str,
      'stack-type': stack_type_validator,
      'queue-count': int,
      'nic-type': nic_type_validator,
      'network-attachment': str,
  }
  parser.add_argument(
      '--network-interface',
      required=required,
      type=arg_parsers.ArgDict(spec=network_interface_spec),
      action='append',
      metavar='PROPERTY=VALUE',
      help=(
          'Adds a network interface to the instance. This flag can be repeated'
          ' to specify multiple network interfaces. The following keys are'
          ' allowed: network, subnet, address, internal-ipv6-address,'
          ' internal-ipv6-prefix-length, external-ipaddress,'
          ' external-ipv6-address, external-ipv6-prefix-length,'
          ' public-ptr-domain, ipv6-public-ptr-domain, network-tier, aliases,'
          ' stack-type, queue-count, nic-type, network-attachment'
      ),
  )
