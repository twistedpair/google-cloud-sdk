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
class InterconnectAttachmentGroupsCompleter(
    compute_completers.ListCommandCompleter
):

  def __init__(self, **kwargs):
    super(InterconnectAttachmentGroupsCompleter, self).__init__(
        collection='compute.interconnectAttachmentGroups',
        list_command='compute interconnects attachments groups list --uri',
        **kwargs,
    )


def InterconnectAttachmentGroupArgument(required=True, plural=False):
  return compute_flags.ResourceArgument(
      resource_name='interconnect attachment group',
      completer=InterconnectAttachmentGroupsCompleter,
      plural=plural,
      required=required,
      global_collection='compute.interconnectAttachmentGroups',
  )


def AddDescription(parser):
  """Adds description flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--description',
      help="""\
      An optional, textual description for the interconnect attachment group.
      """,
  )


def AddIntendedAvailabilitySlaForCreate(parser):
  """Adds IntendedAvailabilitySla flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--intended-availability-sla',
      required=True,
      help="""\
      The availability SLA that the user intends this group to support.
      """,
  )


def AddIntendedAvailabilitySlaForUpdate(parser):
  """Adds IntendedAvailabilitySla flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--intended-availability-sla',
      required=False,
      help="""\
      The availability SLA that the user intends this group to support.
      """,
  )


def AddUpdateMask(parser):
  """Adds UpdateMask flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--update-mask',
      help="""\
      Optional update mask to specify which fields to update. Use commas to
      separate masks. If not specified, all fields present in the command will
      be updated.
      """,
  )


def GetIntendedAvailabilitySla(messages, intended_availability_sla):
  """Converts the intended-availability-sla flag to a message enum.

  Args:
    messages: The API messages holder.
    intended_availability_sla: The intended availability sla flag value.

  Returns:
    An TopologyCapabilityValueValuesEnum of the flag value, or None if absent.
  """
  if intended_availability_sla is None:
    return None
  else:
    return messages.InterconnectAttachmentGroupIntent.AvailabilitySlaValueValuesEnum(
        intended_availability_sla
    )


def GetMemberInterconnectAttachments(parser):
  """Adds attachments flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--attachments',
      type=arg_parsers.ArgList(max_length=16),
      required=True,
      default=[],
      metavar='INTERCONNECT_ATTACHMENT',
      help="""\
      Member interconnect attachments to add to or remove from the interconnect
      attachment group.
      """,
  )


def GetMemberInterconnectAttachmentsForCreate(parser):
  """Adds attachments flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--attachments',
      type=arg_parsers.ArgList(max_length=16),
      required=False,
      default=[],
      metavar='INTERCONNECT_ATTACHMENT',
      help="""\
      Member interconnect attachments to add to the interconnect attachment
      group initially.
      """,
  )


def ParseAttachments(attachments):
  """Converts [region/attachment] to [(region, attachment)]."""
  results = []
  for att in attachments:
    try:
      region, attachment = att.split('/')
    except ValueError:
      raise ValueError(
          f'Invalid attachment: {att}. Must be in the format of region/name'
      )
    results.append((region, attachment))
  return results
