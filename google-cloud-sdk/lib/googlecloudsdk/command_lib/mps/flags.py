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
"""Flags for data-catalog commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.util.apis import yaml_data
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs


def AddInstanceArgToParser(parser, positional=False):
  """Sets up an argument for the instance resource."""
  if positional:
    name = 'instance'
  else:
    name = '--instance'
  instance_data = yaml_data.ResourceYAMLData.FromPath('mps.converge_instance')
  resource_spec = concepts.ResourceSpec.FromYaml(instance_data.GetData())
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name=name,
      concept_spec=resource_spec,
      required=True,
      group_help='instance.')
  return concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)


def AddImageArgToParser(parser, positional=False):
  """Sets up an argument for the image resource."""
  if positional:
    name = 'image'
  else:
    name = '--image'
  image_data = yaml_data.ResourceYAMLData.FromPath('mps.converge_image')
  resource_spec = concepts.ResourceSpec.FromYaml(image_data.GetData())
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name=name,
      concept_spec=resource_spec,
      required=True,
      group_help='image.')
  return concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)


def AddNetworkArgToParser(parser, positional=False):
  """Sets up an argument for the network resource."""
  if positional:
    name = 'network'
  else:
    name = '--network'
  network_data = yaml_data.ResourceYAMLData.FromPath('mps.converge_network')
  resource_spec = concepts.ResourceSpec.FromYaml(network_data.GetData())
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name=name,
      concept_spec=resource_spec,
      required=True,
      group_help='network.')
  return concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)


def AddVolumeArgToParser(parser, positional=False):
  """Sets up an argument for the volume resource."""
  if positional:
    name = 'volume'
  else:
    name = '--volume'
  volume_data = yaml_data.ResourceYAMLData.FromPath('mps.converge_volume')
  resource_spec = concepts.ResourceSpec.FromYaml(volume_data.GetData())
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name=name,
      concept_spec=resource_spec,
      required=True,
      group_help='volume.')
  return concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)


def AddSSHKeyArgToParser(parser, positional=False):
  """Sets up an argument for the image resource."""
  if positional:
    name = 'ssh_key'
  else:
    name = '--ssh_key'
  ssh_key_data = yaml_data.ResourceYAMLData.FromPath('mps.converge_ssh_key')
  resource_spec = concepts.ResourceSpec.FromYaml(ssh_key_data.GetData())
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name=name,
      concept_spec=resource_spec,
      required=True,
      group_help='ssh-key.')
  return concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)


def AddRegionArgToParser(parser, positional=False):
  """Parses region flag."""
  region_data = yaml_data.ResourceYAMLData.FromPath('mps.region')
  resource_spec = concepts.ResourceSpec.FromYaml(region_data.GetData())
  if positional:
    name = 'region'
  else:
    name = '--region'
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name=name,
      concept_spec=resource_spec,
      required=False,
      group_help='region.')
  return concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)
