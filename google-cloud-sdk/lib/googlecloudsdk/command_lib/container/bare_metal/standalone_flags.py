# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""Helpers for flags in commands for Anthos clusters on bare metal."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.container.bare_metal import cluster_flags
from googlecloudsdk.command_lib.util.concepts import concept_parsers


def StandaloneClusterAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='standalone_cluster',
      help_text='cluster of the {resource}.',
  )


def GetStandaloneClusterResourceSpec():
  return concepts.ResourceSpec(
      'gkeonprem.projects.locations.bareMetalStandaloneClusters',
      resource_name='standalone_cluster',
      bareMetalStandaloneClustersId=StandaloneClusterAttributeConfig(),
      locationsId=cluster_flags.LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )


def AddStandaloneClusterResourceArg(
    parser, verb, positional=True, required=True, flag_name_overrides=None
):
  """Adds a resource argument for an Anthos on bare metal standalone cluster.

  Args:
    parser: The argparse parser to add the resource arg to.
    verb: str, the verb to describe the resource, such as 'to update'.
    positional: bool, whether the argument is positional or not.
    required: bool, whether the argument is required or not.
    flag_name_overrides: {str: str}, dict of attribute names to the desired flag
      name.
  """
  name = 'standalone_cluster' if positional else '--cluster'
  concept_parsers.ConceptParser.ForResource(
      name,
      GetStandaloneClusterResourceSpec(),
      'standalone cluster {}'.format(verb),
      required=required,
      flag_name_overrides=flag_name_overrides,
  ).AddToParser(parser)


def StandaloneClusterMembershipIdAttributeConfig():
  """Gets standalone cluster membership ID resource attribute."""
  return concepts.ResourceParameterAttributeConfig(
      name='membership',
      help_text=(
          ' membership of the {resource}, in the form of'
          ' projects/PROJECT/locations/LOCATION/memberships/MEMBERSHIP. '
      ),
  )


def StandaloneClusterMembershipLocationAttributeConfig():
  """Gets standalone cluster membership location resource attribute."""
  return concepts.ResourceParameterAttributeConfig(
      name='location',
      help_text='Google Cloud location for the {resource}.',
  )


def StandaloneClusterMembershipProjectAttributeConfig():
  """Gets Google Cloud project resource attribute."""
  return concepts.ResourceParameterAttributeConfig(
      name='project',
      help_text='Google Cloud project for the {resource}.',
  )


def GetStandaloneClusterMembershipResourceSpec():
  return concepts.ResourceSpec(
      'gkehub.projects.locations.memberships',
      resource_name='membership',
      membershipsId=StandaloneClusterMembershipIdAttributeConfig(),
      locationsId=StandaloneClusterMembershipLocationAttributeConfig(),
      projectsId=StandaloneClusterMembershipProjectAttributeConfig(),
  )


def AddStandaloneClusterMembershipResourceArg(
    parser, **kwargs):
  """Adds a resource argument for a bare metal standalone cluster membership.

  Args:
    parser: The argparse parser to add the resource arg to.
    **kwargs: Additional arguments like positional, required, etc.
  """
  positional = kwargs.get('positional')
  required = kwargs.get('required')
  name = 'membership' if positional else '--membership'
  concept_parsers.ConceptParser.ForResource(
      name,
      GetStandaloneClusterMembershipResourceSpec(),
      (
          'membership of the standalone cluster. Membership can be the'
          ' membership ID or the full resource name.'
      ),
      required=required,
      flag_name_overrides={
          'project': '--membership-project',
          'location': '--membership-location',
      },
  ).AddToParser(parser)
