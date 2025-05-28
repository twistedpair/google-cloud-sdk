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
"""Utilities for flags for `gcloud cloudlocationfinder` commands."""

import sys

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.command_lib.util.concepts import concept_parsers


def LocationAttributeConfig():
  """Returns the attribute config for a Cloud location.

  Returns:
    concepts.ResourceParameterAttributeConfig: Attribute config for a Cloud
      location.
  """
  return concepts.ResourceParameterAttributeConfig(
      name='location',
      help_text='The Cloud location for the {resource}.',
      fallthroughs=[
          deps.Fallthrough(lambda: 'global', 'location is always global')
      ],
  )


def GetLocationResourceSpec():
  """Returns the resource spec for a Cloud location.

  Returns:
    concepts.ResourceSpec: Resource spec for a Cloud location.
  """
  return concepts.ResourceSpec(
      resource_collection='cloudlocationfinder.projects.locations',
      resource_name='location',
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )


def SourceCloudLocationAttributeConfig():
  """Returns the attribute config for a source Cloud location.

  Returns:
    concepts.ResourceParameterAttributeConfig: Attribute config for a source
      Cloud location.
  """
  return concepts.ResourceParameterAttributeConfig(
      name='cloud_location', help_text='The source Cloud location.'
  )


def GetSourceCloudLocationResourceSpec():
  """Returns the resource spec for a source Cloud location.

  Returns:
    concepts.ResourceSpec: Resource spec for a source Cloud location.
  """
  return concepts.ResourceSpec(
      resource_collection=(
          'cloudlocationfinder.projects.locations.cloudLocations'
      ),
      resource_name='source_cloud_location',
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      cloudLocationsId=SourceCloudLocationAttributeConfig(),
  )


def AddLocationFlag(parser, flag_name_overrides=None):
  """Adds a flag for specifying a location.

  Args:
    parser: The parser to add the flag to.
    flag_name_overrides: A dictionary of flag name overrides.
  """
  concept_parsers.ConceptParser.ForResource(
      name='--location',
      resource_spec=GetLocationResourceSpec(),
      group_help='The resource location.',
      required=False,
      flag_name_overrides=flag_name_overrides,
  ).AddToParser(parser)


def AddSourceCloudLocationFlag(parser):
  """Adds a flag for specifying a source Cloud location.

  Args:
    parser: The parser to add the flag to.
  """
  concept_parsers.ConceptParser.ForResource(
      name='--source-cloud-location',
      resource_spec=GetSourceCloudLocationResourceSpec(),
      group_help='The source Cloud location.',
      required=True,
  ).AddToParser(parser)


def AddListFlags(parser):
  """Adds flags for listing Cloudlocations to the given parser.

  Args:
    parser: The parser to add the flags to.
  """
  base.SORT_BY_FLAG.RemoveFromParser(parser)
  AddLocationFlag(parser)


def AddSearchFlags(parser):
  """Adds flags for searching Cloudlocations to the given parser.

  Args:
    parser: The parser to add the flags to.
  """
  AddLocationFlag(parser, flag_name_overrides={'location': ''})
  AddSourceCloudLocationFlag(parser)
  parser.add_argument(
      '--query',
      help='Query to use for searching Cloudlocations.',
  )
  parser.add_argument(
      '--limit',
      type=arg_parsers.BoundedInt(1, sys.maxsize, unlimited=True),
      help='Maximum number of resources to return.',
  )
  parser.add_argument(
      '--page-size',
      type=arg_parsers.BoundedInt(1, sys.maxsize, unlimited=True),
      help='Maximum number of resources per page.',
  )
