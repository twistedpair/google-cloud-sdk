# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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
"""Common flags for artifacts print-settings commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.util.concepts import concept_parsers


def RepoAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='repository', help_text='Repository of the {resource}.')


def LocationAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='location', help_text='Location of the {resource}.')


def GetRepoResourceSpec():
  return concepts.ResourceSpec(
      'artifactregistry.projects.locations.repositories',
      resource_name='repository',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig(),
      repositoriesId=RepoAttributeConfig())


def GetScopeFlag():
  return base.Argument(
      '--scope',
      help=('The scope to associate with the Artifact Registry registry. '
            'If not specified, Artifact Registry is set as the default '
            'registry.'))


def GetRepoFlag():
  return concept_parsers.ConceptParser.ForResource(
      '--repository',
      GetRepoResourceSpec(),
      ('The Artifact Registry repository. If not specified, '
       'the current artifacts/repository is used.'),
      required=False)


def GetLocationResourceSpec():
  return concepts.ResourceSpec(
      'artifactregistry.projects.locations',
      resource_name='location',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig())


def GetLocationFlag():
  return concept_parsers.ConceptParser.ForResource(
      '--location',
      GetLocationResourceSpec(),
      ('The Artifact Registry repository location. If not specified, '
       'the current artifacts/location is used.'),
      required=True)
