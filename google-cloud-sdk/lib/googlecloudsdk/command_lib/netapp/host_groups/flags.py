# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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

"""Flags and helpers for the Cloud NetApp Files Host Groups commands."""

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.netapp import flags
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.command_lib.util.args import labels_util
from googlecloudsdk.command_lib.util.concepts import concept_parsers

## Helper functions to add args / flags for HostGroups gcloud commands ##


def GetHostGroupTypeEnumFromArg(choice, messages):
  """Returns the Choice Enum for Host Group Type.

  Args:
    choice: The choice for host group type as string
    messages: The messages module.

  Returns:
    the host group type enum.
  """
  return arg_utils.ChoiceToEnum(
      choice=choice,
      enum_type=messages.HostGroup.TypeValueValuesEnum,
  )


def GetHostGroupOsTypeEnumFromArg(choice, messages):
  """Returns the Choice Enum for Host Group OS Type.

  Args:
    choice: The choice for host group os type as string
    messages: The messages module.

  Returns:
    the host group os type enum.
  """
  return arg_utils.ChoiceToEnum(
      choice=choice,
      enum_type=messages.HostGroup.OsTypeValueValuesEnum,
  )


def AddHostGroupTypeArg(parser):
  help_text = """\
  String indicating the type of host group.
  The supported values are: 'ISCSI_INITIATOR'
  """

  parser.add_argument(
      '--type',
      type=str,
      help=help_text,
      required=True,
      choices=['ISCSI_INITIATOR'],
  )


def AddHostGroupHostsArg(parser, required=False):
  help_text = """\
  List of hosts in the host group.
  """

  parser.add_argument(
      '--hosts',
      type=arg_parsers.ArgList(min_length=1, element_type=str),
      help=help_text,
      required=required,
      metavar='HOST',
  )


def AddHostGroupOsTypeArg(parser):
  help_text = """\
  String indicating the OS type of the hosts in the host group.
  The supported values are: 'LINUX', 'WINDOWS', 'ESXI'
  """

  parser.add_argument(
      '--os-type',
      type=str,
      help=help_text,
      required=True,
      choices=['LINUX', 'WINDOWS', 'ESXI'],
  )

## Helper function to combine HostGroups args / flags for gcloud commands ##


def AddHostGroupCreateArgs(parser):
  """Add args for creating a Host Group."""
  concept_parsers.ConceptParser([
      flags.GetHostGroupPresentationSpec('The Host Group to create.')
  ]).AddToParser(parser)
  AddHostGroupTypeArg(parser)
  AddHostGroupHostsArg(parser, required=True)
  AddHostGroupOsTypeArg(parser)
  flags.AddResourceDescriptionArg(parser, 'Host Group')
  flags.AddResourceAsyncFlag(parser)
  labels_util.AddCreateLabelsFlags(parser)


def AddHostGroupUpdateArgs(parser):
  """Add args for updating a Host Group."""
  concept_parsers.ConceptParser([
      flags.GetHostGroupPresentationSpec('The Host Group to update.')
  ]).AddToParser(parser)
  AddHostGroupHostsArg(parser, required=False)
  flags.AddResourceDescriptionArg(parser, 'Host Group')
  flags.AddResourceAsyncFlag(parser)
  labels_util.AddUpdateLabelsFlags(parser)
