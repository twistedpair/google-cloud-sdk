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
"""Shared resource flags for Edgenetwork commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs


def LocationAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='location', help_text='The Cloud location for the {resource}.')


def ZoneAttributeConfig(name='zone'):
  return concepts.ResourceParameterAttributeConfig(
      name=name,
      help_text='The zone of the {resource}.',
      completion_request_params={'fieldMask': 'name'},
      completion_id_field='id')


def SubnetAttributeConfig(name='subnet'):
  return concepts.ResourceParameterAttributeConfig(
      name=name,
      help_text='The subnet of the {resource}.',
      completion_request_params={'fieldMask': 'name'},
      completion_id_field='id')


def GetRouterResourceSpec(resource_name='router'):
  return concepts.ResourceSpec(
      'edgenetwork.projects.locations.zones.routers',
      resource_name=resource_name,
      routersId=SubnetAttributeConfig(name=resource_name),
      zonesId=ZoneAttributeConfig('zone'),
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      disable_auto_completers=False)


def AddRouterResourceArg(parser, verb, positional=False):
  """Add a resource argument for a GDCE router.

  Args:
    parser: the parser for the command.
    verb: str, the verb to describe the resource, such as 'to create'.
    positional: bool, if True, means that the resource is a positional rather
      than a flag.
  """
  if positional:
    name = 'router'
  else:
    name = '--router'

  resource_specs = [
      presentation_specs.ResourcePresentationSpec(
          name,
          GetRouterResourceSpec(),
          'The router {}.'.format(verb),
          required=True)
  ]
  concept_parsers.ConceptParser(resource_specs).AddToParser(parser)
