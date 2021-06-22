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

"""Shared resource flags for blueprints commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.core import properties


def DeploymentAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='deployment',
      help_text='The deployment for the {resource}.')


def RevisionAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='revision',
      help_text='The revision for the {resource}.')


def LocationAttributeConfig():
  fallthroughs = [
      deps.PropertyFallthrough(properties.VALUES.blueprints.location)]
  return concepts.ResourceParameterAttributeConfig(
      name='location',
      fallthroughs=fallthroughs,
      help_text='The Cloud location for the {resource}.')


def GetDeploymentResourceSpec():
  return concepts.ResourceSpec(
      'config.projects.locations.deployments',
      resource_name='deployment',
      deploymentsId=DeploymentAttributeConfig(),
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      disable_auto_completers=False)


def GetRevisionResourceSpec():
  return concepts.ResourceSpec(
      'config.projects.locations.deployments.revisions',
      resource_name='revision',
      deploymentsId=DeploymentAttributeConfig(),
      revisionsId=RevisionAttributeConfig(),
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      disable_auto_completers=False)


def AddDeploymentResourceArg(parser, group_help):
  """Add a resource argument for a blueprints deployment.

  NOTE: Must be used only if it's the only resource arg in the command.

  Args:
    parser: the parser for the command.
    group_help: string, the help text for the entire arg group.
  """
  name = 'deployment'
  concept_parsers.ConceptParser.ForResource(
      name,
      GetDeploymentResourceSpec(),
      group_help,
      required=True).AddToParser(parser)


def AddRevisionResourceArg(parser, group_help):
  """Add a resource argument for a blueprints revision.

  NOTE: Must be used only if it's the only resource arg in the command.

  Args:
    parser: the parser for the command.
    group_help: string, the help text for the entire arg group.
  """
  name = 'revision'
  concept_parsers.ConceptParser.ForResource(
      name,
      GetRevisionResourceSpec(),
      group_help,
      required=True).AddToParser(parser)
