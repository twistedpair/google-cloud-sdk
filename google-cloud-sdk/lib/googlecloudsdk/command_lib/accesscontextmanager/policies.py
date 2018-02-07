# Copyright 2018 Google Inc. All Rights Reserved.
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
"""Command line processing utilities for access policies."""
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.core import properties


def GetAttributeConfig():
  property_ = properties.VALUES.access_context_manager.policy
  return concepts.ResourceParameterAttributeConfig(
      name='policy',
      help_text='The ID of the access policy.',
      fallthroughs=[deps.PropertyFallthrough(property_)])


def GetResourceSpec():
  return concepts.ResourceSpec(
      'accesscontextmanager.accessPolicies',
      resource_name='policy',
      accessPoliciesId=GetAttributeConfig())


def AddResourceArg(parser, verb):
  """Add a resource argument for an access policy.

  NOTE: Must be used only if it's the only resource arg in the command.

  Args:
    parser: the parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
  """
  concept_parsers.ConceptParser.ForResource(
      'policy',
      GetResourceSpec(),
      'The access policy {}.'.format(verb),
      required=True).AddToParser(parser)


