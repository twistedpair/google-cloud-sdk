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
"""Shared resource flags for Cloud IoT commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


def GetOperationResource(op):
  return resources.REGISTRY.ParseRelativeName(
      op.name, collection='gkemulticloud.projects.locations.operations')


def AzureClusterAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='cluster', help_text='Azure cluster of the {resource}.')


def AzureNodePoolAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='nodepool', help_text='Azure node pool of the {resource}.')


def AzureClientAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='client', help_text='Azure client of the {resource}.')


def LocationAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='location',
      help_text='Anthos GKE Multi-cloud location for the {resource}.',
      fallthroughs=[deps.PropertyFallthrough(properties.VALUES.azure.location)])


def GetLocationResourceSpec():
  return concepts.ResourceSpec(
      'gkemulticloud.projects.locations',
      resource_name='location',
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG)


def GetAzureClusterResourceSpec():
  return concepts.ResourceSpec(
      'gkemulticloud.projects.locations.azureClusters',
      resource_name='cluster',
      azureClustersId=AzureClusterAttributeConfig(),
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG)


def GetAzureNodePoolResourceSpec():
  return concepts.ResourceSpec(
      'gkemulticloud.projects.locations.azureClusters.azureNodePools',
      resource_name='nodepool',
      azureNodePoolsId=AzureNodePoolAttributeConfig(),
      azureClustersId=AzureClusterAttributeConfig(),
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG)


def GetAzureClientResourceSpec():
  return concepts.ResourceSpec(
      'gkemulticloud.projects.locations.azureClients',
      resource_name='client',
      azureClientsId=AzureClientAttributeConfig(),
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG)


def AddAzureClusterResourceArg(parser, verb, positional=True):
  """Add a resource argument for an Azure cluster.

  Args:
    parser: The argparse.parser to add the resource arg to.
    verb: str, the verb to describe the resource, such as 'to update'.
    positional: bool, whether the argument is positional or not.
  """
  name = 'cluster' if positional else '--cluster'
  concept_parsers.ConceptParser.ForResource(
      name,
      GetAzureClusterResourceSpec(),
      'Azure cluster {}.'.format(verb),
      required=True).AddToParser(parser)


def AddAzureNodePoolResourceArg(parser, verb, positional=True):
  """Add a resource argument for an Azure node pool.

  Args:
    parser: The argparse.parser to add the resource arg to.
    verb: str, the verb to describe the resource, such as 'to update'.
    positional: bool, whether the argument is positional or not.
  """
  name = 'nodepool' if positional else '--nodepool'
  concept_parsers.ConceptParser.ForResource(
      name,
      GetAzureNodePoolResourceSpec(),
      'Azure node pool {}.'.format(verb),
      required=True).AddToParser(parser)


def AddAzureClientResourceArg(parser, verb, positional=True):
  """Add a resource argument for an Azure client.

  Args:
    parser: The argparse.parser to add the resource arg to.
    verb: str, the verb to describe the resource, such as 'to update'.
    positional: bool, whether the argument is positional or not.
  """
  name = 'client' if positional else '--client'
  concept_parsers.ConceptParser.ForResource(
      name,
      GetAzureClientResourceSpec(),
      'Azure client {}.'.format(verb),
      required=True).AddToParser(parser)


def AddLocationResourceArg(parser, verb):
  """Add a location resource.

  Args:
    parser: The argparse.parser to add the resource arg to.
    verb: str, the verb to describe the resource, such as 'to list'.
  """
  concept_parsers.ConceptParser.ForResource(
      '--location',
      GetLocationResourceSpec(),
      'Azure location {}.'.format(verb),
      required=True).AddToParser(parser)


def ParseAzureClientResourceArg(args):
  return args.CONCEPTS.client.Parse()


def ParseAzureClusterResourceArg(args):
  return args.CONCEPTS.cluster.Parse()


def ParseAzureNodePoolResourceArg(args):
  return args.CONCEPTS.nodepool.Parse()
