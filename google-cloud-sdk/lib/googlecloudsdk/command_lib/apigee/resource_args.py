# -*- coding: utf-8 -*- # Lint as: python3
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
"""Specifications for resource-identifying command line parameters."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import collections
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.util.concepts import concept_parsers

_EntityNames = collections.namedtuple(
    "EntityNames", "singular plural docs_name secondary_description")
_ENTITY_TUPLES = [
    _EntityNames("organization", "organizations", "organization",
                 "The organization for the {resource}."),
    _EntityNames("api", "apis", "API proxy",
                 "The API proxy for the {resource}."),
    _EntityNames("environment", "environments", "environment",
                 "The deployment environment of the {resource}."),
    _EntityNames("revision", "revisions", "revision",
                 "The appropriate revision of the {resource}."),
    _EntityNames("deployment", "deployments", "deployment",
                 "The relevant deployment of the {resource}."),
    _EntityNames("operation", "operations", "operation",
                 "The operation operating on the {resource}."),
]
ENTITIES = {item.singular: item for item in _ENTITY_TUPLES}


def AttributeConfig(name, fallthroughs=None, help_text=None):
  """Returns a ResourceParameterAttributeConfig for the attribute named `name`.

  Args:
    name: singular name of the attribute. Must exist in ENTITIES.
    fallthroughs: optional list of gcloud fallthrough objects which should be
      used to get this attribute's value if the user doesn't specify one.
    help_text: help text to use for this resource parameter instead of the
      default help text for the attribute.
  """
  return concepts.ResourceParameterAttributeConfig(
      name=name,
      parameter_name=ENTITIES[name].plural,
      help_text=help_text or ENTITIES[name].secondary_description,
      fallthroughs=fallthroughs)


def ResourceSpec(path, fallthroughs=tuple(), help_texts=None):
  """Returns a ResourceSpec for the resource path `path`.

  Args:
    path: a list of attribute names. All must exist in ENTITIES.
    fallthroughs: optional list of googlecloudsdk.command_lib.apigee.Fallthrough
      objects which will provide default values for the attributes in `path`.
    help_texts: a mapping of attribute names to help text strings, to use
      instead of their default help text.
  """
  help_texts = collections.defaultdict(lambda: None, help_texts or {})
  entities = [ENTITIES[name] for name in path]
  ids = {}
  for entity in entities:
    relevant_fallthroughs = [
        fallthrough for fallthrough in fallthroughs
        if entity.singular in fallthrough
    ]
    config = AttributeConfig(entity.singular, relevant_fallthroughs,
                             help_texts[entity.singular])
    ids[entity.plural + "Id"] = config

  return concepts.ResourceSpec(
      "apigee." + ".".join(entity.plural for entity in entities),
      resource_name=entities[-1].docs_name,
      **ids)


def AddSingleResourceArgument(parser,
                              resource_path,
                              help_text,
                              fallthroughs=tuple(),
                              positional=True,
                              argument_name=None,
                              required=None,
                              prefixes=False,
                              help_texts=None):
  """Creates a concept parser for `resource_path` and adds it to `parser`.

  Args:
    parser: the argparse.ArgumentParser to which the concept parser will be
      added.
    resource_path: path to the resource, in `entity.other_entity.leaf` format.
    help_text: the help text to display when describing the resource as a whole.
    fallthroughs: fallthrough providers for entities in resource_path.
    positional: whether the leaf entity should be provided as a positional
      argument, rather than as a flag.
    argument_name: what to name the leaf entity argument. Defaults to the leaf
      entity name from the resource path.
    required: whether the user is required to provide this resource. Defaults to
      True for positional arguments, False otherwise.
    prefixes: whether to append prefixes to the non-leaf arguments.
    help_texts: custom help text for generated arguments. Defaults to each
      entity using a generic help text.
  """
  split_path = resource_path.split(".")
  if argument_name is None:
    leaf_element_name = split_path[-1]
    if positional:
      argument_name = leaf_element_name.upper()
    else:
      argument_name = "--" + leaf_element_name.replace("_", "-")

  if required is None:
    required = positional

  concept_parsers.ConceptParser.ForResource(
      argument_name,
      ResourceSpec(split_path, fallthroughs, help_texts),
      help_text,
      required=required,
      prefixes=prefixes).AddToParser(parser)
