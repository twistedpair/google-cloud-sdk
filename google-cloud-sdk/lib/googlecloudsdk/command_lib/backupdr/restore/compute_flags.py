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
from googlecloudsdk.command_lib.backupdr import util


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
  parser.add_argument(
      '--target-project',
      type=str,
      required=required,
      help='Project where the restore should happen.',
  )


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


def AddServiceAccountArg(parser, required=True):
  """Service account used to restore."""
  parser.add_argument(
      '--service-account',
      type=str,
      required=required,
      help=(
          'A service account is an identity attached to the instance. Its'
          ' access tokens can be accessed through the instance metadata server'
          ' and are used to authenticate applications on the instance. The'
          ' account can be set using an email address corresponding to the'
          ' required service account. If not provided, the instance will use'
          " the project's default service account."
      ),
  )


def AddScopesArg(parser, required=True):
  """Scopes for the service account used to restore."""
  scopes_group = parser.add_mutually_exclusive_group()

  scopes_group.add_argument(
      '--scopes',
      type=arg_parsers.ArgList(str),
      required=required,
      metavar='SCOPE',
      help=(
          'If not provided, the instance will be assigned the default scopes,'
          ' described below. However, if neither --scopes nor --no-scopes are'
          ' specified and the project has no default service account, then the'
          ' instance will be created with no scopes. Note that the level of'
          ' access that a service account has is determined by a combination of'
          ' access scopes and IAM roles so you must configure both access'
          ' scopes and IAM roles for the service account to work properly.'
          ' SCOPE can be either the full URI of the scope or an alias. Default'
          ' scopes are assigned to all instances. Available aliases are:'
          ' https://cloud.google.com/sdk/gcloud/reference/compute/instances/create#--scopes'
      ),
  )

  scopes_group.add_argument(
      '--no-scopes',
      action='store_true',
      help='Create the instance with no scopes.',
  )
