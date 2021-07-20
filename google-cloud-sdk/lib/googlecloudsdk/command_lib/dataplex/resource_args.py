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
"""Shared resource args for Cloud Dataplex surface."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.util.concepts import concept_parsers


def GetLakeResourceSpec():
  """Gets Lake resource spec."""
  return concepts.ResourceSpec(
      'dataplex.projects.locations.lakes',
      resource_name='lakes',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig(),
      lakesId=LakeAttributeConfig())


def GetZoneResourceSpec():
  """Gets Zone resource spec."""
  return concepts.ResourceSpec(
      'dataplex.projects.locations.lakes.zones',
      resource_name='zones',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig(),
      lakesId=LakeAttributeConfig(),
      zonesId=ZoneAttributeConfig())


def GetAssetResourceSpec():
  """Gets Asset resource spec."""
  return concepts.ResourceSpec(
      'dataplex.projects.locations.lakes.zones.assets',
      resource_name='assets',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig(),
      lakesId=LakeAttributeConfig(),
      zonesId=ZoneAttributeConfig(),
      assetsId=AssetAttributeConfig())


def LocationAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='location', help_text='Location to which the {resource} belongs.')


def LakeAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='lake', help_text='The name of the {resource} to use.')


def ZoneAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='zone', help_text='The name of the {resource} to use.')


def AssetAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='asset', help_text='The name of the {resource} to use.')


def AddLakeResourceArg(parser, verb, positional=True):
  """Adds a resource argument for a Dataplex Lake."""
  name = 'lake' if positional else '--lake'
  return concept_parsers.ConceptParser.ForResource(
      name, GetLakeResourceSpec(), 'The Lake {}'.format(verb),
      required=True).AddToParser(parser)


def AddZoneResourceArg(parser, verb, positional=True):
  """Adds a resource argument for a Dataplex Zone."""
  name = 'zone' if positional else '--zone'
  return concept_parsers.ConceptParser.ForResource(
      name, GetZoneResourceSpec(), 'The Zone {}'.format(verb),
      required=True).AddToParser(parser)


def AddAssetResourceArg(parser, verb, positional=True):
  """Adds a resource argument for a Dataplex Asset."""
  name = 'asset' if positional else '--asset'
  return concept_parsers.ConceptParser.ForResource(
      name, GetAssetResourceSpec(), 'The Asset {}'.format(verb),
      required=True).AddToParser(parser)
