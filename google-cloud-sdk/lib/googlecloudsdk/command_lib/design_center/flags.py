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
"""Design Center Command Lib Flags."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.util.concepts import concept_parsers


def GetProjectResourceSpec():
  return concepts.ResourceSpec(
      'designcenter.projects',
      resource_name='project',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )


def GetProjectResourceArg(
    arg_name='project',
    help_text=None,
    positional=False,
    required=True,
):
  """Constructs and returns the Project Resource Argument."""
  help_text = help_text or 'Project ID.'
  return concept_parsers.ConceptParser.ForResource(
      '{}{}'.format('' if positional else '--', arg_name),
      GetProjectResourceSpec(),
      help_text,
      required=required,
  )


def LocationAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='location',
      help_text='The Cloud location for the {resource}.',
  )


def GetLocationResourceSpec():
  return concepts.ResourceSpec(
      'designcenter.projects.locations',
      resource_name='location',
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )


def GetLocationResourceArg(
    arg_name='location',
    help_text=None,
    positional=False,
    required=True,
):
  """Constructs and returns the Location Resource Argument."""

  help_text = help_text or 'Location.'

  return concept_parsers.ConceptParser.ForResource(
      '{}{}'.format('' if positional else '--', arg_name),
      GetLocationResourceSpec(),
      help_text,
      required=required,
  )


def SpaceResourceAttributeConfig(arg_name, help_text):
  """Helper function for constructing ResourceAttributeConfig."""

  return concepts.ResourceParameterAttributeConfig(
      name=arg_name,
      help_text=help_text,
  )


def GetSpaceResourceSpec(arg_name='space', help_text=None):
  """Constructs and returns the Resource specification for Space."""

  return concepts.ResourceSpec(
      'designcenter.projects.locations.spaces',
      resource_name='space',
      spacesId=SpaceResourceAttributeConfig(arg_name, help_text),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig(),
  )


def GetSpaceResourceArg(
    arg_name='space', help_text=None, positional=True, required=True
):
  """Constructs and returns the Space ID Resource Argument."""

  help_text = help_text or 'The Space ID.'

  return concept_parsers.ConceptParser.ForResource(
      '{}{}'.format('' if positional else '--', arg_name),
      GetSpaceResourceSpec(arg_name, help_text),
      help_text,
      required=required,
  )


def AddDescribeLocationFlags(parser):
  GetLocationResourceArg(positional=True).AddToParser(parser)


def AddGetIamPolicyFlags(parser):
  GetSpaceResourceArg().AddToParser(parser)


def AddSetIamPolicyFlags(parser):
  GetSpaceResourceArg().AddToParser(parser)


def AddTestIamPermissionsFlags(parser):
  GetSpaceResourceArg().AddToParser(parser)
