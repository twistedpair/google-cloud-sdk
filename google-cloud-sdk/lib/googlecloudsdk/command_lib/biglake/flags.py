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
"""Common flags for BigLake commands."""

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.util.concepts import concept_parsers

# A resource argument for a BigLake location.
# This defines how to parse the project and location from the command line.
def GetCatalogResourceSpec():
  """Gets the resource spec for a BigLake location."""
  return concepts.ResourceSpec(
      'biglake.iceberg.v1.restcatalog.v1.projects.catalogs',
      resource_name='catalog',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      catalogsId=concepts.ResourceParameterAttributeConfig(
          'catalog', 'The Iceberg Catalog for the resource.'
      ),
  )


def AddCatalogResourceArg(parser, verb):
  """Adds a resource argument for a BigLake location.

  Args:
    parser: The argparse parser.
    verb: The verb to describe the resource, e.g., "to list catalogs from".
  """
  concept_parsers.ConceptParser.ForResource(
      'catalog',
      GetCatalogResourceSpec(),
      f'The Iceberg Catalog {verb}.',
      required=True,
  ).AddToParser(parser)
