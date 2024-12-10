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
"""Flags and helpers for the compute interconnects groups commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute import completers as compute_completers
from googlecloudsdk.command_lib.compute import flags as compute_flags


@base.UniverseCompatible
@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class InterconnectGroupsCompleter(compute_completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(InterconnectGroupsCompleter, self).__init__(
        collection='compute.interconnectGroups',
        list_command='compute interconnects groups list --uri',
        **kwargs
    )


def InterconnectGroupArgument(required=True, plural=False):
  return compute_flags.ResourceArgument(
      resource_name='interconnect group',
      completer=InterconnectGroupsCompleter,
      plural=plural,
      required=required,
      global_collection='compute.interconnectGroups',
  )


def AddDescription(parser):
  """Adds description flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--description',
      help='An optional, textual description for the interconnect group.',
  )


def AddIntendedTopologyCapabilityForCreate(parser):
  """Adds IntendedTopologyCapability flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--intended-topology-capability',
      required=True,
      help="""\
      The reliability the user intends this group to be capable of, in terms of
      the Interconnect product SLAs.
      """,
  )


def AddIntendedTopologyCapabilityForUpdate(parser):
  """Adds IntendedTopologyCapability flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--intended-topology-capability',
      required=False,
      help="""\
      The reliability the user intends this group to be capable of, in terms of
      the Interconnect product SLAs.
      """,
  )


def GetTopologyCapability(messages, intended_topology_capability):
  """Converts the intended-topology-capability flag to a message enum.

  Args:
    messages: The API messages holder.
    intended_topology_capability: The intended topology capability flag value.

  Returns:
    An TopologyCapabilityValueValuesEnum of the flag value, or None if absent.
  """
  if intended_topology_capability is None:
    return None
  else:
    return messages.InterconnectGroupIntent.TopologyCapabilityValueValuesEnum(
        intended_topology_capability
    )


def GetMemberInterconnects(parser):
  """Adds interconnects flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--interconnects',
      type=arg_parsers.ArgList(max_length=16),
      required=True,
      default=[],
      metavar='INTERCONNECT',
      help="""\
      Member interconnects to add to or remove from the interconnect group.
      """,
  )


def GetMemberInterconnectsForCreate(parser):
  """Adds interconnects flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--interconnects',
      type=arg_parsers.ArgList(max_length=16),
      required=False,
      default=[],
      metavar='INTERCONNECT',
      help="""\
      Member interconnects to add to the interconnect group initially.
      """,
  )


def GetMemberInterconnectsForUpdate(parser):
  """Adds interconnects flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--interconnects',
      type=arg_parsers.ArgList(max_length=16),
      required=False,
      default=[],
      metavar='INTERCONNECT',
      help="""\
      Member interconnects to set the interconnect group to contain.
      """,
  )
