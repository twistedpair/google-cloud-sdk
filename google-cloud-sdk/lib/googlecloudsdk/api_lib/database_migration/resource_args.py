# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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

"""Shared resource flags for Cloud Database Migration Service commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.util.concepts import concept_parsers


def ConnectionProfileAttributeConfig(name='connection_profile'):
  return concepts.ResourceParameterAttributeConfig(
      name=name,
      help_text='The connection profile of the {resource}.',
      completion_request_params={'fieldMask': 'name'},
      completion_id_field='id')


def RegionAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='region',
      help_text='The Cloud region for the {resource}.')


def GetConnectionProfileResourceSpec(resource_name='connection_profile'):
  return concepts.ResourceSpec(
      'datamigration.projects.locations.connectionProfiles',
      resource_name=resource_name,
      connectionProfilesId=ConnectionProfileAttributeConfig(name=resource_name),
      locationsId=RegionAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      disable_auto_completers=False)


def GetRegionResourceSpec():
  return concepts.ResourceSpec(
      'datamigration.projects.locations',
      resource_name='region',
      locationsId=RegionAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG)


def AddConnectionProfileResourceArg(parser, verb, positional=True):
  """Add a resource argument for a database migration connection profile.

  Args:
    parser: the parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
    positional: bool, if True, means that the resource is a positional rather
      than a flag.
  """
  if positional:
    name = 'connection_profile'
  else:
    name = '--connection-profile'
  concept_parsers.ConceptParser.ForResource(
      name,
      GetConnectionProfileResourceSpec(),
      'The connection profile {}.'.format(verb),
      required=True).AddToParser(parser)


def AddRegionResourceArg(parser, verb):
  """Add a resource argument for a database migration region.

  NOTE: Must be used only if it's the only resource arg in the command.

  Args:
    parser: the parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
  """
  concept_parsers.ConceptParser.ForResource(
      '--region',
      GetRegionResourceSpec(),
      'The Cloud region {}.'.format(verb),
      required=True).AddToParser(parser)
