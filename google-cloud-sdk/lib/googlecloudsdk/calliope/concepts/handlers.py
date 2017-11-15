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

import functools

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps as deps_lib
from googlecloudsdk.calliope.concepts import util
from googlecloudsdk.core import exceptions


class Error(exceptions.Error):
  """Base class for errors in this module."""


class ParseError(Error):
  """Raised if a concept fails to parse."""

  def __init__(self, presentation_name, message):
    msg = 'Error parsing [{}].\n{}'.format(presentation_name, message)
    super(ParseError, self).__init__(msg)


class RuntimeHandler(object):
  """A handler to hold information about all concept arguments in a command.

  The handler is assigned to 'CONCEPTS' in the argparse namespace and has an
  attribute to match the name of each concept argument in lower snake case.
  """

  def __init__(self):
    # This is set by the ArgumentInterceptor later.
    self.parsed_args = None

  def ParsedArgs(self):
    """Basically a lazy property to use during lazy concept parsing."""
    return self.parsed_args

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

      def __init__(self, arg_getter):
        self.parse = functools.partial(Parse, concept_spec, concept_info)
        self.arg_getter = arg_getter

      def Parse(self):
        try:
          return self.parse(self.arg_getter())
        except concepts.InitializeError as e:
          raise ParseError(name, e.message)

    setattr(self, name, LazyParse(self.ParsedArgs))


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

  def _BuildFinalFallthroughsMap(self, parsed_args=None):
    """Helper method to build all fallthroughs including arg names."""
    final_fallthroughs_map = {}
    for attribute in self.concept_spec.attributes:
      attribute_name = attribute.name
      attribute_fallthroughs = []

      # Start the fallthroughs list with the primary associated arg for the
      # attribute.
      arg_name = self.attribute_to_args_map.get(attribute_name)
      if arg_name:
        arg_value = getattr(parsed_args,
                            util.NamespaceFormat(arg_name),
                            None)
        # Required positionals end up stored as lists of strings.
        if isinstance(arg_value, list) and attribute.value_type == str:
          arg_value = arg_value[0] if arg_value else None
        attribute_fallthroughs.append(
            deps_lib.ArgFallthrough(arg_name, arg_value))

      attribute_fallthroughs += self.fallthroughs_map.get(attribute_name, [])
      final_fallthroughs_map[attribute_name] = attribute_fallthroughs
    return final_fallthroughs_map

  def GetDeps(self, parsed_args=None):
    """Builds the deps.Deps object to get attribute values.

    Gets a set of fallthroughs for each attribute of the handler's concept spec,
    including any argument values that were registered through RegisterArg.
    Then initializes the deps object.

    Args:
      parsed_args: (calliope.parser_extensions.Namespace) the parsed arguments
        from command line.

    Returns:
      (deps_lib.Deps) the deps object representing all data dependencies.
    """
    final_fallthroughs_map = self._BuildFinalFallthroughsMap(
        parsed_args=parsed_args)
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


def Parse(concept_spec, concept_info, parsed_args=None):
  """Parses a concept at runtime.

  Args:
    concept_spec: googlecloudsdk.calliope.concepts.ConceptSpec, The underlying
      concept spec.
    concept_info: ConceptInfo, the object that holds dependencies of the
      concept.
    parsed_args: (calliope.parser_extensions.Namespace) the parsed arguments
      from command line.

  Returns:
    The fully initialized concept.

  Raises:
    googlecloudsdk.calliope.concepts.concepts.InitializeError, if the concept
      can't be initialized.
  """
  deps = concept_info.GetDeps(parsed_args=parsed_args)
  return concept_spec.Initialize(deps)
