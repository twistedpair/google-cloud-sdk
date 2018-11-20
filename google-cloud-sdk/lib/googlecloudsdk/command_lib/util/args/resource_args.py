# -*- coding: utf-8 -*- #
# Copyright 2016 Google Inc. All Rights Reserved.
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
"""Module for resource_args API support."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.util.apis import yaml_data
from googlecloudsdk.command_lib.util.concepts import concept_parsers


def AddResourceArgToParser(parser,
                           resource_path,
                           help_text,
                           name=None,
                           required=True):
  """Adds a resource argument in a python command.

  Args:
    parser: the parser for the command.
    resource_path: string, the resource_path which refers to the resources.yaml.
    help_text: string, the help text of the resource argument.
    name: string, the default is the name specified in the resources.yaml file.
    required: boolean, the default is True because in most cases resource arg is
      required.
  """
  resource_yaml_data = yaml_data.ResourceYAMLData.FromPath(resource_path)
  resource_spec = concepts.ResourceSpec.FromYaml(resource_yaml_data.GetData())
  concept_parsers.ConceptParser.ForResource(
      name=(name if name else resource_yaml_data.GetArgName()),
      resource_spec=resource_spec,
      group_help=help_text,
      required=required).AddToParser(parser)
