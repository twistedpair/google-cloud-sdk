# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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
"""Shared resource flags for Cloud Composer commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.util.concepts import concept_parsers


def AddLocationResourceArg(parser,
                           verb,
                           positional=True,
                           required=True,
                           plural=False,
                           help_supplement=None):
  """Add a resource argument for a Cloud Composer location.

  Fallthroughs are disabled if the argument is plural, as this would cause
  the fallthrough processor to iterate over each character in the fallthrough
  value and parse it as a location ID.

  NOTE: Must be used only if it's the only resource arg in the command.

  Args:
    parser: the parser for the command
    verb: str, the verb to describe the resource, for example, 'to update'.
    positional: boolean, if True, means that the resource is a positional rather
      than a flag.
    required: boolean, if True, the arg is required
    plural: boolean, if True, expects a list of resources
    help_supplement: str, Supplementary help text specific to the command in
      which the resource arg is being used..
  """
  help_supplement = help_supplement or ''
  noun = 'location' + ('s' if plural else '')
  name = _BuildArgName(noun, positional)
  concept_parsers.ConceptParser.ForResource(
      name,
      GetLocationResourceSpec(),
      'The {} {}. {}'.format(noun, verb, help_supplement),
      required=required,
      plural=plural).AddToParser(parser)


def GetLocationResourceSpec():
  return concepts.ResourceSpec(
      'composerflex.projects.locations',
      resource_name='location',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig())


def LocationAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='location',
      help_text='Compute Engine region in which to create the {resource}.',
  )


def AddContextResourceArg(parser,
                          verb,
                          positional=True,
                          required=True,
                          plural=False):
  """Add a resource argument for a Cloud Composer context entity.

  NOTE: Must be used only if it's the only resource arg in the command.

  Args:
    parser: the parser for the command
    verb: str, the verb to describe the resource, for example, 'to update'.
    positional: boolean, if True, means that the resource is a positional rather
      than a flag.
    required: boolean, if True, the arg is required
    plural: boolean, if True, expects a list of resources
  """
  noun = 'context' + ('s' if plural else '')
  name = _BuildArgName(noun, positional)
  concept_parsers.ConceptParser.ForResource(
      name,
      GetContextResourceSpec(),
      'The {} {}.'.format(noun, verb),
      required=required,
      plural=plural).AddToParser(parser)


def GetContextResourceSpec():
  return concepts.ResourceSpec(
      'composerflex.projects.locations.contexts',
      resource_name='context',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig(),
      contextsId=ContextAttributeConfig())


def ContextAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='context', help_text='Cloud Composer context for the {resource}.')


def _BuildArgName(name, positional):
  return '{}{}'.format('' if positional else '--', name)

