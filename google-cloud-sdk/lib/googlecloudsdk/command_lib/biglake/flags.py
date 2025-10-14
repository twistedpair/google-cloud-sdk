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


# A resource argument for a BigLake Iceberg catalog.
# This defines how to parse the project and catalog from the command line.
def GetCatalogResourceSpec():
  """Gets the resource spec for a BigLake Iceberg catalog."""
  return concepts.ResourceSpec(
      'biglake.iceberg.v1.restcatalog.v1.projects.catalogs',
      resource_name='catalog',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      catalogsId=concepts.ResourceParameterAttributeConfig(
          'catalog', 'The Iceberg Catalog for the resource.'
      ),
  )


def GetNamespaceResourceSpec():
  """Gets the resource spec for a BigLake Iceberg namespace."""
  return concepts.ResourceSpec(
      'biglake.iceberg.v1.restcatalog.v1.projects.catalogs.namespaces',
      resource_name='namespace',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      catalogsId=concepts.ResourceParameterAttributeConfig(
          'catalog', 'The Iceberg Catalog for the resource.'
      ),
      namespacesId=concepts.ResourceParameterAttributeConfig(
          'namespace', 'The Iceberg Namespace for the resource.'
      ),
  )


def GetTableResourceSpec():
  """Gets the resource spec for a BigLake Iceberg table."""
  return concepts.ResourceSpec(
      'biglake.iceberg.v1.restcatalog.v1.projects.catalogs.namespaces.tables',
      resource_name='table',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      catalogsId=concepts.ResourceParameterAttributeConfig(
          'catalog', 'The Iceberg Catalog for the resource.'
      ),
      namespacesId=concepts.ResourceParameterAttributeConfig(
          'namespace', 'The Iceberg Namespace for the resource.'
      ),
      tablesId=concepts.ResourceParameterAttributeConfig(
          'table', 'The Iceberg Table for the resource.'
      ),
  )


def AddCatalogResourceArg(parser, verb, positional=True):
  """Adds a resource argument for a BigLake Iceberg catalog.

  Args:
    parser: The argparse parser.
    verb: The verb to describe the resource, e.g., "to list catalogs from".
    positional: Whether the argument should be positional or a flag.
  """
  concept_parsers.ConceptParser.ForResource(
      'catalog' if positional else '--catalog',
      GetCatalogResourceSpec(),
      f'The Iceberg Catalog {verb}.',
      required=True,
  ).AddToParser(parser)


def AddNamespaceResourceArg(parser, verb, positional=True):
  """Adds a resource argument for a BigLake Iceberg namespace.

  Args:
    parser: The argparse parser.
    verb: The verb to describe the resource, e.g., "to list namespaces from".
    positional: Whether the argument should be positional or a flag.
  """
  concept_parsers.ConceptParser.ForResource(
      'namespace' if positional else '--namespace',
      GetNamespaceResourceSpec(),
      f'The Iceberg Namespace {verb}.',
      required=True,
  ).AddToParser(parser)


def AddTableResourceArg(parser, verb, positional=True):
  """Adds a resource argument for a BigLake Iceberg table.

  Args:
    parser: The argparse parser.
    verb: The verb to describe the resource, e.g., "to list tables from".
    positional: Whether the argument should be positional or a flag.
  """
  concept_parsers.ConceptParser.ForResource(
      'table' if positional else '--table',
      GetTableResourceSpec(),
      f'The Iceberg Table {verb}.',
      required=True,
  ).AddToParser(parser)
