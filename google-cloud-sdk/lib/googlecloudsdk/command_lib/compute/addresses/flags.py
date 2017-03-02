# Copyright 2016 Google Inc. All Rights Reserved.
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

"""Flags and helpers for the compute addresses commands."""

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.compute import flags as compute_flags
from googlecloudsdk.command_lib.compute.forwarding_rules import flags as forwarding_flags


def AddressArgument(required=True):
  return compute_flags.ResourceArgument(
      resource_name='address name',
      completion_resource_id='compute.address',
      plural=True,
      required=required,
      regional_collection='compute.addresses',
      global_collection='compute.globalAddresses',
      short_help='The address names to operate on.',
      region_explanation=compute_flags.REGION_PROPERTY_EXPLANATION)


def AddAddresses(parser):
  """Adds the Addresses flag."""
  parser.add_argument(
      '--addresses',
      metavar='ADDRESS',
      type=arg_parsers.ArgList(min_length=1),
      help="""\
      Ephemeral IP addresses to promote to reserved status. Only addresses
      that are being used by resources in the project can be promoted. When
      providing this flag, a parallel list of names for the addresses can
      be provided. For example,

          $ {command} ADDRESS-1 ADDRESS-2 \
            --addresses 162.222.181.197,162.222.181.198 \
            --region us-central1

      will result in 162.222.181.197 being reserved as
      'ADDRESS-1' and 162.222.181.198 as 'ADDRESS-2'. If
      no names are given, server-generated names will be assigned
      to the IP addresses.
      """)


def AddAddressesAndIPVersions(parser, required=True):
  """Adds Addresses and IP versions flag."""
  group = parser.add_mutually_exclusive_group(required=required)
  forwarding_flags.AddIpVersionGroup(group)
  AddAddresses(group)


def AddDescription(parser):
  """Adds the Description flag."""
  parser.add_argument(
      '--description',
      help='An optional textual description for the addresses.')
