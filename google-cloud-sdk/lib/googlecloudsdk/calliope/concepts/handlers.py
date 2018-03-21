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

from __future__ import absolute_import
import abc

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps as deps_lib
from googlecloudsdk.calliope.concepts import util
from googlecloudsdk.core import exceptions
import six


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
    self._arg_name_lookup = {}

  def ParsedArgs(self):
    """Basically a lazy property to use during lazy concept parsing."""
    return self.parsed_args

  def AddConcept(self, name, concept_info, required=True):
    """Adds a concept handler for a given concept.

    Args:
      name: str, the name to be used for the presentation spec.
      concept_info: ConceptInfo, the object that holds dependencies of the
        concept.
      required: bool, True if the concept must be parseable, False if not.
    """

    class LazyParse(object):

      def __init__(self, parse, arg_getter):
        self.parse = parse
        self.arg_getter = arg_getter

      def Parse(self):
        try:
          return self.parse(self.arg_getter())
        except concepts.InitializationError as e:
          if required:
            raise ParseError(name, e.message)
          return None

    setattr(self, name, LazyParse(concept_info.Parse, self.ParsedArgs))
    for _, arg_name in six.iteritems(concept_info.attribute_to_args_map):
      self._arg_name_lookup[util.NormalizeFormat(arg_name)] = concept_info

  def ArgNameToConceptInfo(self, arg_name):
    return self._arg_name_lookup.get(util.NormalizeFormat(arg_name))


class ConceptInfo(six.with_metaclass(abc.ABCMeta, object)):
  """Holds information for a concept argument.

  The ConceptInfo object is responsible for holding information about the
  dependencies of a concept, and building a Deps object when it is time for
  lazy parsing of the concept.

  Attributes:
    concept_spec: The concept spec underlying the concept handler.
    attribute_to_args_map: A map of attributes to the names of their associated
      flags.
    fallthroughs_map: A map of attributes to non-argument fallthroughs.
  """

  @abc.abstractmethod
  def Parse(self, parsed_args=None):
    """Lazy parsing function to parse concept.

    Args:
      parsed_args: the argparse namespace from the runtime handler.

    Returns:
      the parsed concept.
    """

  @abc.abstractmethod
  def GetHints(self, attribute_name):
    """Get a list of string hints for how to specify a concept's attribute.

    Args:
      attribute_name: str, the name of the attribute to get hints for.

    Returns:
      [str], a list of string hints.
    """


class ResourceInfo(object):
  """Holds information for a resource argument."""

  def __init__(self, concept_spec, attribute_to_args_map,
               fallthroughs_map, plural=False, allow_empty=False):
    """Initializes the ConceptInfo.

    Args:
      concept_spec: googlecloudsdk.calliope.concepts.ConceptSpec, The underlying
        concept spec.
      attribute_to_args_map: {str: str}, A map of attribute names to the names
        of their associated flags.
      fallthroughs_map: {str: [deps_lib.Fallthrough]} A map of attribute names
        to non-argument fallthroughs.
      plural: bool, True if multiple resources can be parsed, False otherwise.
      allow_empty: bool, True if resource parsing is allowed to return no
        resource, otherwise False.
    """
    self.concept_spec = concept_spec
    self.attribute_to_args_map = attribute_to_args_map
    self.fallthroughs_map = fallthroughs_map
    self.plural = plural
    self.allow_empty = allow_empty

    self._result = None
    self._result_computed = False

  @property
  def resource_spec(self):
    return self.concept_spec

  def BuildFullFallthroughsMap(self, parsed_args=None):
    """Builds map of all fallthroughs including arg names.

    Fallthroughs are a list of objects that, when called, try different ways of
    getting values for attributes (see googlecloudsdk.calliope.concepts.deps.
    _Fallthrough). This method builds a map from the name of each attribute to
    its fallthroughs, including the "primary" fallthrough representing its
    corresponding argument value in parsed_args if any, and any fallthroughs
    that were configured for the attribute beyond that.

    Args:
      parsed_args: the parsed namespace.

    Returns:
      {str: [deps_lib._Fallthrough]}, a map from attribute name to its
      fallthroughs.
    """
    fallthroughs_map = {}
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
        # The only args that should be lists are anchor args for plural
        # resources.
        plural = (attribute_name == self.concept_spec.anchor.name
                  and self.plural)
        if isinstance(arg_value, list) and not plural:
          arg_value = arg_value[0] if arg_value else None
        if plural and arg_value is None:
          arg_value = []
        attribute_fallthroughs.append(
            deps_lib.ArgFallthrough(arg_name, arg_value))

      attribute_fallthroughs += self.fallthroughs_map.get(attribute_name, [])
      fallthroughs_map[attribute_name] = attribute_fallthroughs
    return fallthroughs_map

  def GetHints(self, attribute_name):
    """Gets a list of string hints for how to set an attribute.

    Given the attribute name, gets a list of hints corresponding to the
    attribute's fallthroughs.

    Args:
      attribute_name: str, the name of the attribute.

    Returns:
      A list of hints for its fallthroughs, including its primary arg if any.
    """
    fallthroughs = self.BuildFullFallthroughsMap().get(attribute_name, [])
    return [f.hint for f in fallthroughs]

  def Parse(self, parsed_args=None):
    """Lazy, cached parsing function for resource.

    Args:
      parsed_args: the parsed Namespace.

    Returns:
      the initialized resource or a list of initialized resources if the
        resource argument was pluralized.
    """
    if not self._result_computed:
      result = self._ParseUncached(parsed_args)
      self._result_computed = True
      self._result = result
    return self._result

  def _ParseUncached(self, parsed_args=None):
    """Lazy parsing function for resource.

    Args:
      parsed_args: the parsed Namespace.

    Returns:
      the initialized resource or a list of initialized resources if the
        resource argument was pluralized.
    """
    fallthroughs_map = self.BuildFullFallthroughsMap(parsed_args)

    if not self.plural:
      try:
        return self.concept_spec.Initialize(deps_lib.Deps(fallthroughs_map))
      except concepts.InitializationError:
        if self.allow_empty:
          return None
        raise

    anchor = self.concept_spec.anchor.name
    anchor_fallthroughs = fallthroughs_map.get(anchor, [])

    # Iterate through the values provided to the anchor argument, creating for
    # each a separate parsed resource.
    resources = []
    for i, fallthrough in enumerate(anchor_fallthroughs):

      try:
        anchor_values = fallthrough.GetValue()
      except deps_lib.FallthroughNotFoundError:
        continue
      for arg_value in anchor_values:
        def F(return_value=arg_value):
          return return_value
        fallthrough = deps_lib.Fallthrough(F, fallthrough.hint)
        fallthroughs_map[anchor] = (
            anchor_fallthroughs[:i] + [fallthrough] +
            anchor_fallthroughs[i:])
        resources.append(self.concept_spec.Initialize(deps_lib.Deps(
            fallthroughs_map)))
      return resources
    if self.allow_empty:
      return resources
    return self.concept_spec.Initialize(deps_lib.Deps(
        fallthroughs_map))
