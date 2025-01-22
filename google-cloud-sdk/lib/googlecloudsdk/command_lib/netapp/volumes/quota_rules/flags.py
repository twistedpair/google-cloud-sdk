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

"""Flags and helpers for the Cloud NetApp Files Volume QuotaRules commands."""

from googlecloudsdk.command_lib.netapp import flags
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.command_lib.util.args import labels_util
from googlecloudsdk.command_lib.util.concepts import concept_parsers

## Helper functions to add args / flags for QuotaRules gcloud commands ##


def GetQuotaRuleTypeEnumFromArg(choice, messages):
  """Returns the Choice Enum for Quota Rule Type.

  Args:
    choice: The choice for quota rule type as string
    messages: The messages module.

  Returns:
    the quota rule type enum.
  """
  return arg_utils.ChoiceToEnum(
      choice=choice,
      enum_type=messages.QuotaRule.TypeValueValuesEnum,
  )


def AddQuotaRuleVolumeArg(parser, required=False):
  concept_parsers.ConceptParser.ForResource(
      '--volume',
      flags.GetVolumeResourceSpec(positional=False),
      'The volume for which quota rule applies.',
      flag_name_overrides={'location': ''},
      required=required,
  ).AddToParser(parser)


def AddQuotaRuleTypeArg(parser):
  help_text = """\
  String indicating the type of quota rule.
  The supported values are: 'DEFAULT_USER_QUOTA','DEFAULT_GROUP_QUOTA','INDIVIDUAL_USER_QUOTA','INDIVIDUAL_GROUP_QUOTA'
  """

  parser.add_argument(
      '--type',
      type=str,
      help=help_text,
      required=True,
  )


def AddQuotaRuleTargetArg(parser):
  help_text = """\
  The target of the quota rule.
  Identified by a Unix UID/GID, Windows SID, or null for default.
  """

  parser.add_argument(
      '--target',
      type=str,
      help=help_text,
  )


def AddQuotaRuleDiskLimitMib(parser, required=False):
  help_text = 'The disk limit in MiB for the quota rule.'

  parser.add_argument(
      '--disk-limit-mib',
      type=int,
      help=help_text,
      required=required,
  )

## Helper function to combine QuotaRules args / flags for gcloud commands ##


def AddQuotaRuleCreateArgs(parser):
  """Add args for creating a Quota rule."""
  concept_parsers.ConceptParser([
      flags.GetQuotaRulePresentationSpec('The Quota rule to create.')
  ]).AddToParser(parser)
  AddQuotaRuleVolumeArg(parser, required=True)
  AddQuotaRuleTypeArg(parser)
  AddQuotaRuleTargetArg(parser)
  AddQuotaRuleDiskLimitMib(parser, required=True)
  flags.AddResourceDescriptionArg(parser, 'Quota rule')
  flags.AddResourceAsyncFlag(parser)
  labels_util.AddCreateLabelsFlags(parser)


def AddQuotaRuleUpdateArgs(parser):
  """Add args for updating a Quota rule."""
  concept_parsers.ConceptParser([
      flags.GetQuotaRulePresentationSpec('The Quota rule to update.')
  ]).AddToParser(parser)
  AddQuotaRuleVolumeArg(parser, required=True)
  AddQuotaRuleDiskLimitMib(parser, required=False)
  flags.AddResourceDescriptionArg(parser, 'Quota rule')
  flags.AddResourceAsyncFlag(parser)
  labels_util.AddUpdateLabelsFlags(parser)
