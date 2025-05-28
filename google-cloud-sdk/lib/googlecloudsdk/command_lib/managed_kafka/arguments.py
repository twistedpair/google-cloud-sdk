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
"""Module for Managed Kafka arguments."""

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.util.apis import yaml_data
from googlecloudsdk.command_lib.util.concepts import concept_parsers


def AddSchemaRegistryArgToParser(parser):
  """Sets up an argument for the schema registry resource."""
  schema_registry_data = yaml_data.ResourceYAMLData.FromPath(
      'managed_kafka.schema_registry'
  )
  concept_parsers.ConceptParser.ForResource(
      'schema_registry',
      concepts.ResourceSpec.FromYaml(
          schema_registry_data.GetData(), is_positional=True
      ),
      'The schema registry to create.',
      required=True,
  ).AddToParser(parser)


def AddSubjectArgToParser(parser):
  """Sets up an argument for the subject resource."""
  subject_data = yaml_data.ResourceYAMLData.FromPath('managed_kafka.subject')
  concept_parsers.ConceptParser.ForResource(
      'subject',
      concepts.ResourceSpec.FromYaml(
          subject_data.GetData(), is_positional=True
      ),
      'The subject to create.',
      required=True,
  ).AddToParser(parser)
