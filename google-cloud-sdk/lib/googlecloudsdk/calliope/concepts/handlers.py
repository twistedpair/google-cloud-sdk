# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Classes for runtime handling of concept arguments."""

import argparse
import functools

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps as deps_lib
from googlecloudsdk.core import exceptions


class Error(exceptions.Error):
  """Base class for errors in this module."""


class ParseError(Error):
  """Raised if a concept fails to parse."""

  def __init__(self, presentation_name, message):
    msg = 'Error parsing [{}].\n{}'.format(presentation_name, message)
    super(ParseError, self).__init__(msg)


class ConceptArgActionGetter(object):
  """Class that builds concept arg argparse actions for a given command."""

  def __init__(self, runtime_handler):
    """Initializes ConceptArgActionGetter.

    Args:
      runtime_handler: RuntimeHandler, the object responsible for concepts in
        this command.
    """
    self.runtime_handler = runtime_handler

  def Get(self, presentation_name, attribute_name):
    """Builds an argparse action for attribute flags.

    Args:
      presentation_name: str, the name of the concept in its presentation spec.
      attribute_name: str, the name of the attribute.

    Returns:
      (AttributeAction) The custom argparse action that registers the arg with
        the runtime handler.
    """
    def Register(value):
      """Registers an arg to a runtime handler."""
      self.runtime_handler.RegisterArg(presentation_name, attribute_name, value)

    def RegisterHandlerIn(namespace):
      """Registers the runtime handler in argparse namespace."""
      setattr(namespace, 'CONCEPTS', self.runtime_handler)

    class AttributeAction(argparse.Action):
      """An action that registers the arg in the runtime handler."""

      def __init__(self, *args, **kwargs):
        kwargs.pop('completer', None)
        super(AttributeAction, self).__init__(*args, **kwargs)

      def __call__(self, parser, namespace, value, option_string=None):
        del parser, option_string
        if isinstance(value, list):
          if value:
            value = value[0]
        RegisterHandlerIn(namespace)
        Register(value)

    return AttributeAction


class RuntimeHandler(object):
  """A handler to hold information about all concept arguments in a command.

  The handler is assigned to 'CONCEPTS' in the argparse namespace and has an
  attribute to match the name of each concept argument.
  """

  def __init__(self):
    """Initializes a RuntimeHandler."""
    self._concept_info_registry = {}

  def AddConcept(self, name, concept_spec, concept_info):
    """Adds a concept handler for a given concept.

    Args:
      name: str, the name to be used for the presentation spec.
      concept_spec: googlecloudsdk.calliope.concepts.ConceptSpec, the spec for
        the underlying concept.
      concept_info: ConceptInfo, the object that holds dependencies of the
        concept.
    """

    class LazyParse(object):

      def __init__(self):
        self.parse = functools.partial(Parse, concept_spec, concept_info)

      def Parse(self):
        try:
          return self.parse()
        except concepts.InitializeError as e:
          raise ParseError(name, e.message)

    setattr(self, name, LazyParse())
    self._concept_info_registry[name] = concept_info

  def RegisterArg(self, presentation_name, attribute, value):
    """Registers an argument to a certain concept by attribute.

    Args:
      presentation_name: str, the presentation spec's name for the concept, in
        namespace format (lower snake case, no prefix '--').
      attribute: str, the name of the attribute.
      value: the parsed value from argparse, usually a string.
    """
    concept_info = self._concept_info_registry.get(presentation_name, None)
    if concept_info:
      concept_info.RegisterArg(attribute, value)


class ConceptInfo(object):
  """Holds information for a concept argument.

  The ConceptInfo object is responsible for holding information about the
  dependencies of a concept, and building a Deps object when it is time for
  lazy parsing of the concept.

  Attributes:
    concept_spec: The concept spec underlying the concept handler.
    attribute_to_args_map: A map of attributes to the names of their associated
      flags.
    fallthroughs_map: A map of attributes to non-argument fallthroughs.
    arg_info_map: A map of attribute names to values passed to the corresponding
      flag.
  """

  def __init__(self, concept_spec, attribute_to_args_map,
               fallthroughs_map):
    """Initializes the ConceptInfo.

    Args:
      concept_spec: googlecloudsdk.calliope.concepts.ConceptSpec, The underlying
        concept spec.
      attribute_to_args_map: {str: str}, A map of attribute names to the names
        of their associated flags.
      fallthroughs_map: {str: [deps_lib.Fallthrough]} A map of attribute names
        to non-argument fallthroughs.
    """
    self.concept_spec = concept_spec
    self.attribute_to_args_map = attribute_to_args_map
    self.fallthroughs_map = fallthroughs_map
    self.arg_info_map = {}

  def RegisterArg(self, attribute, value):
    """Registers the value of an attribute flag.

    Args:
      attribute: str, the name of the attribute.
      value: the parsed value from argparse (often string, but depends on the
        type of the argument.
    """
    self.arg_info_map[attribute] = value

  def _BuildFinalFallthroughsMap(self):
    """Helper method to build all fallthroughs including arg names."""
    final_fallthroughs_map = {}
    for attribute in self.concept_spec.attributes:
      attribute_name = attribute.name
      attribute_fallthroughs = []

      # Start the fallthroughs list with the primary associated arg for the
      # attribute.
      arg_name = self.attribute_to_args_map.get(attribute_name)
      if arg_name:
        arg_info = self.arg_info_map.get(attribute_name, None)
        attribute_fallthroughs.append(
            deps_lib.ArgFallthrough(arg_name, arg_info))

      attribute_fallthroughs += self.fallthroughs_map.get(attribute_name, [])
      final_fallthroughs_map[attribute_name] = attribute_fallthroughs
    return final_fallthroughs_map

  def GetDeps(self):
    """Builds the deps.Deps object to get attribute values.

    Gets a set of fallthroughs for each attribute of the handler's concept spec,
    including any argument values that were registered through RegisterArg.
    Then initializes the deps object.

    Returns:
      (deps_lib.Deps) the deps object representing all data dependencies.
    """
    final_fallthroughs_map = self._BuildFinalFallthroughsMap()
    return deps_lib.Deps(final_fallthroughs_map)

  def GetHints(self, attribute_name):
    """Gets a list of string hints for how to set an attribute.

    Given the attribute name, gets a list of hints corresponding to the
    attribute's fallthroughs.

    Args:
      attribute_name: str, the name of the attribute.

    Returns:
      A list of hints for its fallthroughs, including its primary arg if any.
    """
    fallthroughs = self._BuildFinalFallthroughsMap().get(attribute_name, [])
    return [f.hint for f in fallthroughs]


def Parse(concept_spec, concept_info):
  """Parses a concept at runtime.

  Args:
    concept_spec: googlecloudsdk.calliope.concepts.ConceptSpec, The underlying
      concept spec.
    concept_info: ConceptInfo, the object that holds dependencies of the
      concept.

  Returns:
    The fully initialized concept.

  Raises:
    googlecloudsdk.calliope.concepts.concepts.InitializeError, if the concept
      can't be initialized.
  """
  deps = concept_info.GetDeps()
  return concept_spec.Initialize(deps)
