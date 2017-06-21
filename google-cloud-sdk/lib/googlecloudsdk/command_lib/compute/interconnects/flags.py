# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Flags and helpers for the compute interconnects commands."""

from googlecloudsdk.command_lib.compute import flags as compute_flags


def InterconnectArgument(required=True, plural=False):
  return compute_flags.ResourceArgument(
      resource_name='interconnect',
      completion_resource_id='compute.interconnects',
      plural=plural,
      required=required,
      global_collection='compute.interconnects')


def InterconnectArgumentForOtherResource(short_help,
                                         required=True,
                                         detailed_help=None):
  return compute_flags.ResourceArgument(
      name='--interconnect',
      resource_name='interconnect',
      completion_resource_id='compute.interconnects',
      plural=False,
      required=required,
      global_collection='compute.interconnects',
      short_help=short_help,
      detailed_help=detailed_help)


def ResolveInterconnectEnumValues(args, holder):
  """Converts input arg into enum type."""
  interconnect = holder.client.messages.Interconnect
  if args.interconnect_type and args.interconnect_type in ['IT_PRIVATE']:
    interconnect_type = interconnect.InterconnectTypeValueValuesEnum.IT_PRIVATE
  else:
    interconnect_type = None

  if args.link_type and args.link_type in ['LINK_TYPE_ETHERNET_10G_LR']:
    link_type = interconnect.LinkTypeValueValuesEnum.LINK_TYPE_ETHERNET_10G_LR
  else:
    link_type = None
  return {'interconnect_type': interconnect_type, 'link_type': link_type}


def AddInterconnectType(parser):
  """Adds interconnect-type flag to the argparse."""
  parser.add_argument(
      '--interconnect-type',
      choices=['IT_PRIVATE'],
      required=True,
      help="""\
      Type of the interconnect.
      """)


def AddLinkType(parser):
  """Adds link-type flag to the argparse."""
  parser.add_argument(
      '--link-type',
      choices=['LINK_TYPE_ETHERNET_10G_LR'],
      required=True,
      help="""\
      Type of the link requested.
      """)


def AddRequestedLinkCount(parser):
  """Adds requestedLinkCount flag to the argparse."""
  parser.add_argument(
      '--requested-link-count',
      required=True,
      type=int,
      help="""\
      Target number of physical links in the link bundle, as requested by the
      customer.
      """)


def AddRequestedLinkCountForPatch(parser):
  """Adds requestedLinkCount flag to the argparse."""
  parser.add_argument(
      '--requested-link-count',
      type=int,
      help="""\
      Target number of physical links in the link bundle, as requested by the
      customer.
      """)


def AddNocContactEmail(parser):
  """Adds nocContactEmail flag to the argparse."""
  parser.add_argument(
      '--noc-contact-email',
      help="""\
      Email address to contact the customer NOC for operations and maintenance
      notifications regarding this Interconnect.
      """)


def AddAdminEnabled(parser):
  """Adds adminEnabled flag to the argparse."""
  admin_enabled_args = parser.add_mutually_exclusive_group()
  admin_enabled_args.add_argument(
      '--admin-enabled',
      action='store_true',
      default=None,
      help="""\
      Administrative status of the interconnect. When this is provided, the
      Interconnect is functional and may carry traffic (assuming there are
      functional InterconnectAttachments and other requirements are satisfied).
      """)
