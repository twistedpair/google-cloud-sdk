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


def LocationAttributeConfig():
  """Returns the resource parameter attribute config for location."""
  return concepts.ResourceParameterAttributeConfig(
      name='location',
      help_text='The Cloud location for the {resource}.',
  )


def CollectionAttributeConfig():
  """Returns the resource parameter attribute config for collection."""
  return concepts.ResourceParameterAttributeConfig(
      name='collection',
      help_text='The name of the {resource}.',
  )


def GetDataObjectResourceSpec():
  """Returns the resource spec for data object."""
  return concepts.ResourceSpec(
      'vectorsearch.projects.locations.collections.dataObjects',
      resource_name='dataObject',
      disable_auto_completers=False,
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig(),
      collectionsId=CollectionAttributeConfig(),
  )


def AddCollectionFlag(parser, help_verb):
  """Adds --collection flag to the parser."""
  parser.add_argument(
      '--collection',
      required=True,
      help=f'The collection to {help_verb} data objects from.',
  )


def AddLocationFlag(parser):
  """Adds --location flag to the parser."""
  parser.add_argument(
      '--location', required=True, help='Location of the collection.'
  )


def AddJsonFilterFlag(parser, help_verb):
  """Adds --json-filter flag to the parser."""
  parser.add_argument(
      '--json-filter',
      help=(
          f'A filter expression in JSON format to apply to the {help_verb},'
          ' e.g. \'{"genre": {"$eq": "sci-fi"}}\'.'
      ),
  )


def AddDataObjectFlags(parser, command_name):
  """Adds flags for query data object command."""
  AddCollectionFlag(parser, command_name)
  AddLocationFlag(parser)
  AddJsonFilterFlag(parser, command_name)
