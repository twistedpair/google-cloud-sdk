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

from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute import completers as compute_completers
from googlecloudsdk.command_lib.compute import flags as compute_flags


_BANDWIDTH_ALLOCATION_CHOICES = {
    'ALLOCATE_PER_WIRE': 'Allocate per wire.',
    'SHARED_WITH_WIRE_GROUP': 'Shared with wire group.'
}

_NETWORK_SERVICE_CLASS_CHOICES = {
    'BRONZE': 'Bronze.',
    'GOLD': 'Gold.'
}

_WIRE_GROUP_TYPE = {
    'WIRE': 'Wire',
    'REDUNDANT': 'Redundant',
    'BOX_AND_CROSS': 'Box and cross',
}


@base.UniverseCompatible
@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class WireGroupsCompleter(compute_completers.ListCommandCompleter):

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


def AddDescription(parser):
  """Adds description flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--description',
      help='An optional, textual description for the wire group.',
  )


def AddCrossSiteNetwork(parser):
  """Adds cross-site-network flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--cross-site-network',
      required=True,
      help='A cross site network for the wire group.',
  )


def AddType(parser):
  """Adds type flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--type',
      required=True,
      choices=_WIRE_GROUP_TYPE,
      help='The type for the wire group.',
  )


def AddBandwidthUnmetered(parser):
  """Adds bandwidth-unmetered flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--bandwidth-unmetered',
      required=True,
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
      choices={'NONE': 'None', 'DISABLED_PORT': 'Disabled port'},
      help='The fault response for the wire group.',
  )


def AddAdminEnabled(parser):
  """Adds admin-enabled flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--admin-enabled',
      help='Set admin-enabled on the wire group.',
  )


def AddNetworkServiceClass(parser):
  """Adds network-service-class flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--network-service-class',
      choices=_NETWORK_SERVICE_CLASS_CHOICES,
      help='The network service class for the wire group.',
  )


def AddBandwidthAllocation(parser):
  """Adds bandwidth-allocation flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--bandwidth-allocation',
      choices=_BANDWIDTH_ALLOCATION_CHOICES,
      help='The bandwidth allocation for the wire group.',
  )


def AddValidateOnly(parser):
  """Adds validate-only flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--validate-only',
      help='Only validates the configuration, but does not create it.',
  )


