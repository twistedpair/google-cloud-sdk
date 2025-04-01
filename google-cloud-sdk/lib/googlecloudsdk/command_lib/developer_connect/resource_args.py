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
"""Shared resource argument definitions for Developer Connect Commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.util.concepts import concept_parsers


def InsightConfigAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='insightsConfigs',
      help_text='The registry of the insight config.')


def RegionAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='location',
      help_text='The region of the insight config.')


def GetInsightConfigSpec():
  return concepts.ResourceSpec(
      'developerconnect.projects.locations.insightsConfigs',
      resource_name='insights_config',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=RegionAttributeConfig(),
      insightsConfigsId=InsightConfigAttributeConfig(),
      disable_auto_completers=False,
  )


def AddInsightConfigResourceArg(parser, verb):
  """Adds an insight config resource argument to the parser."""
  concept_parsers.ConceptParser.ForResource(
      'insights_config',
      GetInsightConfigSpec(),
      'The insights config to {}.'.format(verb),
      required=True,
  ).AddToParser(parser)
