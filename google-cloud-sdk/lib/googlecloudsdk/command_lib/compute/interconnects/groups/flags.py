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
from googlecloudsdk.command_lib.compute.interconnects import flags as interconnect_flags


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


def GetInterconnectType(messages, interconnect_type_arg):
  """Converts the interconnect type flag to a message enum.

  Args:
    messages: The API messages holder.
    interconnect_type_arg: The interconnect type flag value.

  Returns:
    An InterconnectTypeValueValuesEnum of the flag value, or None if absent.
  """
  if interconnect_type_arg is None:
    return None
  else:
    return messages.InterconnectGroupsCreateMembersInterconnectInput.InterconnectTypeValueValuesEnum(
        interconnect_type_arg
    )


def GetLinkType(messages, link_type_arg):
  """Converts the link type flag to a message enum.

  Args:
    messages: The API messages holder.
    link_type_arg: The link type flag value.

  Returns:
    An LinkTypeValueValuesEnum of the flag value, or None if absent.
  """
  if link_type_arg is None:
    return None
  else:
    return messages.InterconnectGroupsCreateMembersInterconnectInput.LinkTypeValueValuesEnum(
        link_type_arg
    )


def GetRequestedFeatures(messages, requested_features_arg):
  """Converts the requested-features flag to a list of message enums.

  Args:
    messages: The API messages holder.
    requested_features_arg: A list of the interconnect feature type flag values.

  Returns:
    A list of RequestedFeaturesValueListEntryValuesEnum values, or None if
    absent.
  """
  if not requested_features_arg:
    return []
  return list(
      set(
          filter(
              None,
              (
                  GetRequestedFeature(messages, f)
                  for f in requested_features_arg
              ),
          )
      )
  )


def GetRequestedFeature(messages, feature_arg):
  """Converts interconnect feature type flag to a message enum.

  Args:
    messages: The API messages holder.
    feature_arg: The feature type flag value.

  Returns:
    A RequestedFeaturesValueListEntryValuesEnum of the flag value.
  """
  if feature_arg == 'MACSEC':
    return messages.InterconnectGroupsCreateMembersInterconnectInput.RequestedFeaturesValueListEntryValuesEnum(
        'IF_MACSEC'
    )
  if feature_arg == 'CROSS_SITE_NETWORK':
    return messages.InterconnectGroupsCreateMembersInterconnectInput.RequestedFeaturesValueListEntryValuesEnum(
        'IF_CROSS_SITE_NETWORK'
    )
  return None


def AddFacility(parser):
  """Adds facility flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--facility',
      help='The facility (zone free location) to create the interconnect in.',
  )


def AddRemoteLocation(parser):
  """Adds remote location flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--remote-location',
      help='The location of the interconnect for Cross-Cloud Interconnect.',
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


def AddMemberInterconnectsForCreateMembers(parser):
  """Adds interconnect flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--interconnect',
      type=arg_parsers.ArgDict(
          spec={
              'facility': str,
              'description': str,
              'name': str,
              'link-type': _GetLinkTypeValidator(),
              'requested-link-count': int,
              'interconnect-type': _GetInterconnectTypeValidator(),
              'admin-enabled': None,
              'no-admin-enabled': None,
              'noc-contact-email': str,
              'customer-name': str,
              'remote-location': str,
              'requested-features': arg_parsers.ArgList(
                  choices=interconnect_flags.REQUESTED_FEATURES_CHOICES,
                  custom_delim_char=':',
              ),
          },
          required_keys=['name'],
          allow_key_only=True,
      ),
      action='append',
      required=True,
      metavar='INTERCONNECT',
      help="""\
      New member interconnects to create in the interconnect group. To create
      multiple interconnects, this flag should be specified multiple times.

      Each interconnect takes in the same set of flags as the `gcloud compute
      interconnects create` command, except instead of a location, a facility
      must be specified. These flags are defined as a comma separated list of
      flag=value pairs.

      Example:
      --interconnect name=interconnect1,facility=iad-1,description="my
      interconnect",link-type=LINK_TYPE_ETHERNET_10G_LR,requested-link-count=1,
      interconnect-type=DEDICATED,admin-enabled,
      noc-contact-email=noc@google.com,customer-name=customer-name
      requested-features=MACSEC:CROSS_SITE_NETWORK

      Note that for multiple requested-features, use a colon (:) as the
      delimiter, as the comma is used to separate the flags. Similarly, if you
      need to use a comma in another flag value, you should set an alternative
      delimiter for the --interconnect flag. Run `gcloud topic escaping` for
      more information.
      """,
  )


def _GetLinkTypeValidator():
  """Returns a validator for the link-type flag."""

  def _ValidateLinkType(link_type):
    if link_type is None:
      return True
    return link_type in interconnect_flags.LINK_TYPE_CHOICES

  return arg_parsers.CustomFunctionValidator(
      _ValidateLinkType,
      'Invalid link-type, must be one of: '
      f'[{", ".join(interconnect_flags.LINK_TYPE_CHOICES.keys())}]',
  )


def _GetInterconnectTypeValidator():
  """Returns a validator for the interconnect-type flag."""

  def _ValidateInterconnectType(interconnect_type):
    if interconnect_type is None:
      return True
    return interconnect_type in interconnect_flags.INTERCONNECT_TYPE_CHOICES_GA

  return arg_parsers.CustomFunctionValidator(
      _ValidateInterconnectType,
      'Invalid interconnect-type, must be one of: '
      f'[{", ".join(interconnect_flags.INTERCONNECT_TYPE_CHOICES_GA.keys())}]',
  )


def AddIntentMismatchBehavior(parser):
  """Adds intent mismatch behavior flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--intent-mismatch-behavior',
      choices=['REJECT', 'CREATE'],
      help="""\
      The behavior when the intent of the interconnect group does not match the
      topology capability of the member interconnects.
      """,
  )


def GetIntentMismatchBehavior(messages, intent_mismatch_behavior):
  """Converts the intent mismatch behavior flag to a message enum.

  Args:
    messages: The API messages holder.
    intent_mismatch_behavior: The intent mismatch behavior flag value.

  Returns:
    An IntentMismatchBehaviorValueValuesEnum of the flag value.
  """
  if intent_mismatch_behavior is None:
    return None
  return messages.InterconnectGroupsCreateMembers.IntentMismatchBehaviorValueValuesEnum(
      intent_mismatch_behavior
  )
