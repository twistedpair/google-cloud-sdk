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
"""Shared resource arguments and flags."""

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.util.concepts import concept_parsers


def RegionAttributeConfig():
  """Returns the resource parameter attribute config for region."""
  return concepts.ResourceParameterAttributeConfig(
      name='region',
      help_text='The Cloud region for the {resource}.',
  )


def InvestigationAttributeConfig():
  """Returns the resource parameter attribute config for investigation."""
  return concepts.ResourceParameterAttributeConfig(
      name='investigation',
      help_text='The name of the {resource}.',
  )


def GetInvestigationResourceSpec():
  """Returns the resource spec for investigation."""
  return concepts.ResourceSpec(
      'geminicloudassist.projects.locations.investigations',
      resource_name='investigation',
      disable_auto_completers=False,
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=RegionAttributeConfig(),
      investigationsId=InvestigationAttributeConfig(),
  )


def AddInvestigationResourceArg(
    parser, verb='', help_text_override='', required=True
):
  """Adds investigations resource argument to the parser.

  NOTE: May be used only if it's the only resource arg in the command.
  Args:
    parser: the argparse parser for the command.
    verb: (Optional) str, the verb to describe the resource, such as 'to
      update'.
    help_text_override: (Optional)str, the help text to use for the resource
      argument. If override is providded, verb will be ignored.
    required: bool, whether the argument is required.
  """
  help_text = help_text_override or f'The investigation name {verb}.'
  concept_parsers.ConceptParser.ForResource(
      'investigation',
      GetInvestigationResourceSpec(),
      help_text,
      required=required,
  ).AddToParser(parser)


def AddIAMPolicyFileArg(parser):
  """Adds IAM policy file argument to the parser.

  Args:
    parser: the argparse parser for the command.
  """
  parser.add_argument(
      'policy_file',
      metavar='POLICY_FILE',
      help=(
          'Path to a local JSON or YAML formatted file '
          'containing a valid policy.'
      ),
  )
