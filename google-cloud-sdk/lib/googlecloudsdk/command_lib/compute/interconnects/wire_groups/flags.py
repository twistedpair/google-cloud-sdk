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
"""Flags and helpers for the compute interconnects wire groups commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import textwrap

from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute import completers as compute_completers
from googlecloudsdk.command_lib.compute import flags as compute_flags


_BANDWIDTH_ALLOCATION_CHOICES = {
    'ALLOCATE_PER_WIRE': (
        'Configures a separate unmetered bandwidth allocation (and associated'
        ' charges) for each wire in the group.'
    ),
    'SHARED_WITH_WIRE_GROUP': (
        'Configures one unmetered bandwidth allocation for the wire group. The'
        ' unmetered bandwidth is divided equally across each wire in the group,'
        ' but dynamic throttling reallocates unused unmetered bandwidth from'
        ' unused or underused wires to other wires in the group.'
    ),
}

_NETWORK_SERVICE_CLASS_CHOICES = {
    'BRONZE': 'The lowest service class.',
    'GOLD': 'The highest service class.',
}

_WIRE_GROUP_TYPE = {
    'WIRE': 'Single wire type wire groups must have only one VLAN tag.',
    'REDUNDANT': 'Redundant type wire groups must have only one VLAN tag.',
    'BOX_AND_CROSS': (
        'Box and cross type wire groups must have two VLAN tags. The first is'
        ' for the same-zone pseudowire, and the second is for the cross-zone'
        ' pseudowire.'
    ),
}


@base.UniverseCompatible
@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class WireGroupsCompleter(compute_completers.GlobalListCommandCompleter):

  def __init__(self, **kwargs):
    super(WireGroupsCompleter, self).__init__(
        collection='compute.wireGroups',
        list_command='compute interconnects wire-groups list --uri',
        **kwargs
    )


def WireGroupArgument(required=True, plural=False):
  return compute_flags.ResourceArgument(
      resource_name='wire group',
      completer=WireGroupsCompleter,
      plural=plural,
      required=required,
      global_collection='compute.wireGroups',
  )


def AddCrossSiteNetwork(parser):
  """Adds cross-site-network flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--cross-site-network',
      help='The cross site network for the wire group.',
      required=True,
  )


def AddDescription(parser):
  """Adds description flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--description',
      help='An optional, textual description for the wire group.',
  )


def AddType(parser):
  """Adds type flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--type',
      choices=_WIRE_GROUP_TYPE,
      help=textwrap.dedent('The type for the wire group.')
  )


def AddBandwidthUnmetered(parser, required=True):
  """Adds bandwidth-unmetered flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--bandwidth-unmetered',
      required=required,
      type=int,
      help='The amount of unmetered bandwidth to assign to the wire group.',
  )


def AddBandwidthMetered(parser):
  """Adds bandwidth-metered flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--bandwidth-metered',
      type=int,
      help='The amount of metered bandwidth to assign to the wire group.',
  )


def AddFaultResponse(parser):
  """Adds fault-response flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--fault-response',
      choices={'NONE': 'None', 'DISABLE_PORT': 'Disable port'},
      help='The fault response for the wire group.',
  )


def AddAdminEnabled(parser, update=False):
  """Adds admin-enabled flag to the argparse.ArgumentParser."""
  if update:
    help_text = textwrap.dedent("""\
      Administrative status of the wire group. When this is enabled, the wire
      group is operational and will carry traffic. Use --no-admin-enabled to
      disable it.
      """)
  else:
    help_text = textwrap.dedent("""\
      Administrative status of the wire group. If not provided on creation,
      defaults to enabled. When this is enabled, the wire group is
      operational and will carry traffic. Use --no-admin-enabled to disable
      it.
      """)
  parser.add_argument(
      '--admin-enabled',
      action='store_true',
      default=None,
      help=help_text,
  )


def AddNetworkServiceClass(parser):
  """Adds network-service-class flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--network-service-class',
      choices=_NETWORK_SERVICE_CLASS_CHOICES,
      help=textwrap.dedent('The network service class for the wire group.')
  )


def AddBandwidthAllocation(parser, required=True):
  """Adds bandwidth-allocation flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--bandwidth-allocation',
      choices=_BANDWIDTH_ALLOCATION_CHOICES,
      help='The bandwidth allocation for the wire group.',
      required=required,
  )


def AddValidateOnly(parser):
  """Adds validate-only flag to the argparse.ArgumentParser."""
  help_text = textwrap.dedent("""\
    Validate the new configuration, but don't update it.
    """)
  parser.add_argument(
      '--validate-only',
      action='store_true',
      default=None,
      help=help_text,
  )


def AddEndpointLabel(parser, required=True):
  """Adds endpoint-label flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--endpoint-label',
      required=required,
      help='The endpoint label for the wire group.',
  )


def AddInterconnectLabel(parser, required=True):
  """Adds interconnect-label flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--interconnect-label',
      required=required,
      help='The interconnect label for the wire group endpoint.',
  )


def AddVlanTags(parser, required=True):
  """Adds vlan-tags flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--vlan-tags',
      required=required,
      help='The vlan tags for the interconnect on the wire group endpoint.',
  )
