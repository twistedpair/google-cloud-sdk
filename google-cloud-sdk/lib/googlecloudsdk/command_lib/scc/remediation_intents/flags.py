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
"""Common flags for the SCC RemediationIntent resource commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.util.concepts import concept_parsers


# OrganizationId attribute flag for the resouce
def OrganizationAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='organization',
      help_text='The Google Cloud organization for the {resource}.',
  )


# LocationId attribute flag for the resouce
def LocationAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='location',
      help_text='The Google Cloud location for the {resource}.',
  )


# RemediationIntentId attribute flag for the resouce
def RemediationIntentAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='remediation-intent',
      help_text='The remediation intent for the {resource}.',
  )


# Positional Resource flag
def GetRemediationIntentResourceSpec():
  return concepts.ResourceSpec(
      'securityposture.organizations.locations.remediationIntents',
      resource_name='remediationIntent',
      organizationsId=OrganizationAttributeConfig(),
      locationsId=LocationAttributeConfig(),
      remediationIntentsId=RemediationIntentAttributeConfig(),
      disable_auto_completers=False,
  )


# Add the remediation intent resource argument to the parser
def AddRemediationIntentResourceArg(parser):
  concept_parsers.ConceptParser.ForResource(
      'remediationintent',
      GetRemediationIntentResourceSpec(),
      'The remediation intent resource.',
      required=True,
  ).AddToParser(parser)

# Other flags (positional)
POSITIONAL_PARENT_NAME_FLAG = base.Argument(
    'parent',
    help=""" The parent resource to create the remediation intent under.
        Format: organizations/{org_id}/locations/{loc_id} """,
)


# Other flags (non-positional)
PARENT_NAME_FLAG = base.Argument(
    '--parent',
    help=""" The parent resource to create the remediation intent under.
        Format: organizations/{org_id}/locations/{loc_id} """,
    required=True,
)

FINDING_NAME_FLAG = base.Argument(
    '--finding-name',
    help=""" Canonical name of the SCC finding
        Format: projects/{proj_id}/sources/{src_id}/locations/{loc_id}/findings/{finding_id} """,
    required=False,
)

WORKFLOW_TYPE_FLAG = base.Argument(
    '--workflow-type',
    choices=['semi-autonomous', 'manual'],
    help=""" Type of the workflow to be created""",
    required=True,
)

ETAG_FLAG = base.Argument(
    '--etag',
    help=""" Etag is an optional flag. If the provided Etag doesn't match the server generated Etag, the operation won't proceed.""",
    required=False,
)

REMEDIATION_INTENT_FROM_FILE_FLAG = base.Argument(
    '--ri-from-file',
    help=""" Path to the YAML file containing the remediation intent resource.
              Format: /path/to/file.yaml.""",
    type=arg_parsers.YAMLFileContents(),
    required=True,
)

UPDATE_MASK_FLAG = base.Argument(
    '--update-mask',
    help=""" Comma separated string containing list of fields to be updated.
              Format: field1,field2.""",
    required=False,
)

GIT_CONFIG_FILE_PATH_FLAG = base.Argument(
    '--git-config-path',
    help=""" Path to the git config file in YAML format to raise the PR.
            Format: /path/to/file.yaml. Sample Config file:\n
              remote: origin
              main-branch-name: master
              branch-prefix: iac-remediation-
              reviewers: reviewer1,reviewer2
            """,
    metavar='GIT_SETTINGS',
    type=arg_parsers.YAMLFileContents(),
    required=True,
)

ORG_ID_FLAG = base.Argument(
    '--org-id',
    help=""" The Google Cloud organization ID""",
    required=True,
)

ROOT_DIR_PATH_FLAG = base.Argument(
    '--root-dir-path',
    help=""" The relative path to the root directory for the terraform
    repository.\n If not specified, the default value
    is assumed to be the current directory.""",
    required=False,
)
