# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Helpers for flags in commands working with Anthos clusters on VMware."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.core import properties


def LocationAttributeConfig():
  """Gets Google Cloud location resource attribute."""
  return concepts.ResourceParameterAttributeConfig(
      name='location',
      help_text='Google Cloud location for the {resource}.',
      fallthroughs=[
          deps.PropertyFallthrough(properties.VALUES.container_vmware.location),
      ])


def GetLocationResourceSpec():
  """Constructs and returns the Resource specification for Location."""

  return concepts.ResourceSpec(
      'gkeonprem.projects.locations',
      resource_name='location',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig(),
  )


def AddLocationResourceArg(parser):
  """Adds a resource argument for Google Cloud location.

  Args:
    parser: The argparse.parser to add the resource arg to.
  """
  concept_parsers.ConceptParser.ForResource(
      '--location',
      GetLocationResourceSpec(),
      'Google Cloud location for the {resource}.',
      required=True).AddToParser(parser)


def ClusterAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='cluster',
      help_text='cluster of the {resource}.',
  )


def GetClusterResourceSpec():
  return concepts.ResourceSpec(
      'gkeonprem.projects.locations.vmwareClusters',
      resource_name='cluster',
      vmwareClustersId=ClusterAttributeConfig(),
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )


def AddClusterResourceArg(parser, verb, positional=True):
  """Adds a resource argument for an Anthos cluster on VMware.

  Args:
    parser: The argparse parser to add the resource arg to.
    verb: str, the verb to describe the resource, such as 'to update'.
    positional: bool, whether the argument is positional or not.
  """
  name = 'cluster' if positional else '--cluster'
  concept_parsers.ConceptParser.ForResource(
      name, GetClusterResourceSpec(), 'cluster {}'.format(verb),
      required=True).AddToParser(parser)


def NodePoolAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='node_pool', help_text='node pool of the {resource}.')


def GetNodePoolResourceSpec():
  return concepts.ResourceSpec(
      'gkeonprem.projects.locations.vmwareClusters.vmwareNodePools',
      resource_name='node_pool',
      vmwareNodePoolsId=NodePoolAttributeConfig(),
      vmwareClustersId=ClusterAttributeConfig(),
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )


def AddNodePoolResourceArg(parser, verb, positional=True):
  """Adds a resource argument for a VMware node pool.

  Args:
    parser: The argparse parser to add the resource arg to.
    verb: str, the verb to describe the resource, such as 'to update'.
    positional: bool, whether the argument is positional or not.
  """
  name = 'node_pool' if positional else '--node-pool'
  concept_parsers.ConceptParser.ForResource(
      name,
      GetNodePoolResourceSpec(),
      'node pool {}'.format(verb),
      required=True).AddToParser(parser)
