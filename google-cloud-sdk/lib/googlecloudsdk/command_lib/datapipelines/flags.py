# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Flags and helpers for the compute related commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.util.concepts import concept_parsers


def RegionAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='region', help_text='The Cloud region for the {resource}.')


def GetPipelineResourceArg(arg_name='pipeline',
                           help_text=None,
                           positional=True,
                           required=True):
  """Constructs and returns the Pipeline Resource Argument."""

  def GetPipelineResourceSpec():
    """Constructs and returns the Resource specification for Pipeline."""

    def PipelineAttributeConfig():
      return concepts.ResourceParameterAttributeConfig(
          name=arg_name, help_text=help_text)

    return concepts.ResourceSpec(
        'datapipelines.projects.locations.pipelines',
        resource_name='pipeline',
        pipelinesId=PipelineAttributeConfig(),
        locationsId=RegionAttributeConfig(),
        projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
        disable_auto_completers=False)

  help_text = help_text or 'Name for the Data Pipelines Pipeline.'

  return concept_parsers.ConceptParser.ForResource(
      '{}{}'.format('' if positional else '--', arg_name),
      GetPipelineResourceSpec(),
      help_text,
      required=required)


def AddDescribePipelineFlags(parser):
  GetPipelineResourceArg().AddToParser(parser)


def AddDeletePipelineFlags(parser):
  GetPipelineResourceArg().AddToParser(parser)


def AddStopPipelineFlags(parser):
  GetPipelineResourceArg().AddToParser(parser)


def AddRunPipelineFlags(parser):
  GetPipelineResourceArg().AddToParser(parser)


def AddRegionResourceArg(parser, verb):
  """Add a resource argument for a Vertex AI region.

  NOTE: Must be used only if it's the only resource arg in the command.

  Args:
    parser: the parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
  """
  region_resource_spec = concepts.ResourceSpec(
      'datapipelines.projects.locations',
      resource_name='region',
      locationsId=RegionAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG)

  concept_parsers.ConceptParser.ForResource(
      '--region',
      region_resource_spec,
      'Cloud region {}.'.format(verb),
      required=True).AddToParser(parser)
