# Copyright 2018 Google Inc. All Rights Reserved.
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
from __future__ import unicode_literals
import abc

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps as deps_lib
from googlecloudsdk.calliope.concepts import util
from googlecloudsdk.command_lib.util.concepts import completers
import six
from six.moves import filter  # pylint: disable=redefined-builtin


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

  @property
  def concept_spec(self):
    """The concept spec associated with this info class."""
    raise NotImplementedError

  @property
  def fallthroughs_map(self):
    """A map of attribute names to non-primary fallthroughs."""
    raise NotImplementedError

  @abc.abstractmethod
  def GetHints(self, attribute_name):
    """Get a list of string hints for how to specify a concept's attribute.

    Args:
      attribute_name: str, the name of the attribute to get hints for.

    Returns:
      [str], a list of string hints.
    """

  def GetGroupHelp(self):
    """Get the group help for the group defined by the presentation spec.

    Must be overridden in subclasses.

    Returns:
      (str) the help text.
    """
    raise NotImplementedError

  def GetAttributeArgs(self):
    """Generate args to add to the argument group.

    Must be overridden in subclasses.

    Yields:
      (calliope.base.Argument), all arguments corresponding to concept
        attributes.
    """
    raise NotImplementedError

  def AddToParser(self, parser):
    """Adds all attribute args for the concept to argparse.

    Must be overridden in subclasses.

    Args:
      parser: the parser for the Calliope command.
    """
    raise NotImplementedError

  @abc.abstractmethod
  def Parse(self, parsed_args=None):
    """Lazy parsing function to parse concept.

    Args:
      parsed_args: the argparse namespace from the runtime handler.

    Returns:
      the parsed concept.
    """

  def ClearCache(self):
    """Clear cache if it exists. Override where needed."""
    pass


class ResourceInfo(ConceptInfo):
  """Holds information for a resource argument."""

  def __init__(self, presentation_name, concept_spec, group_help,
               attribute_to_args_map, fallthroughs_map, required=False,
               plural=False, group=None):
    """Initializes the ResourceInfo.

    Args:
      presentation_name: str, the name of the anchor argument of the
        presentation spec.
      concept_spec: googlecloudsdk.calliope.concepts.ConceptSpec, The underlying
        concept spec.
      group_help: str, the group help for the argument group.
      attribute_to_args_map: {str: str}, A map of attribute names to the names
        of their associated flags.
      fallthroughs_map: {str: [deps_lib.Fallthrough]} A map of attribute names
        to non-argument fallthroughs.
      required: bool, False if resource parsing is allowed to return no
        resource, otherwise True.
      plural: bool, True if multiple resources can be parsed, False otherwise.
      group: an argparse argument group parser to which the resource arg group
        should be added, if any.
    """
    self.presentation_name = presentation_name
    self._concept_spec = concept_spec
    self._fallthroughs_map = fallthroughs_map
    self.attribute_to_args_map = attribute_to_args_map
    self.plural = plural
    self.group_help = group_help
    self.allow_empty = not required
    self.group = group

    self._result = None
    self._result_computed = False
    self.sentinel = 0

  @property
  def concept_spec(self):
    return self._concept_spec

  @property
  def resource_spec(self):
    return self.concept_spec

  @property
  def fallthroughs_map(self):
    return self._fallthroughs_map

  @property
  def title(self):
    """The title of the arg group for the spec, in all caps with spaces."""
    name = self.concept_spec.name
    name = name[0].upper() + name[1:]
    return name.replace('_', ' ').replace('-', ' ')

  def BuildFullFallthroughsMap(self):
    """Builds map of all fallthroughs including arg names.

    Fallthroughs are a list of objects that, when called, try different ways of
    getting values for attributes (see googlecloudsdk.calliope.concepts.deps.
    _Fallthrough). This method builds a map from the name of each attribute to
    its fallthroughs, including the "primary" fallthrough representing its
    corresponding argument value in parsed_args if any, and any fallthroughs
    that were configured for the attribute beyond that.

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
        # The only args that should be lists are anchor args for plural
        # resources.
        plural = (attribute_name == self.concept_spec.anchor.name
                  and self.plural)
        attribute_fallthroughs.append(
            deps_lib.ArgFallthrough(arg_name, plural=plural))

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

  def GetGroupHelp(self):
    """Build group help for the argument group."""
    if len(list(filter(bool, self.attribute_to_args_map.values()))) == 1:
      generic_help = 'This represents a Cloud resource.'
    else:
      generic_help = ('The arguments in this group can be used to specify the '
                      'attributes of this resource.')
    description = ['{} resource - {} {}'.format(
        self.title,
        self.group_help,
        generic_help)]
    skip_flags = [
        attribute.name for attribute in self.resource_spec.attributes
        if not self.attribute_to_args_map.get(attribute.name)]
    if skip_flags:
      description.append('(NOTE) Some attributes are not given arguments in '
                         'this group but can be set in other ways.')
      for attr_name in skip_flags:
        hints = self.GetHints(attr_name)
        if not hints:
          # This may be an error, but existence of fallthroughs should not be
          # enforced here.
          continue
        hint = 'To set the [{}] attribute: {}.'.format(
            attr_name,
            '; '.join(hints))
        description.append(hint)
    return ' '.join(description)

  @property
  def args_required(self):
    """True if the resource is required and any arguments have no fallthroughs.

    If fallthroughs can ever be configured in the ResourceInfo object,
    a more robust solution will be needed, e.g. a GetFallthroughsForAttribute
    method.

    Returns:
      bool, whether the argument group should be required.
    """
    if self.allow_empty:
      return False
    anchor = self.resource_spec.anchor
    if (self.attribute_to_args_map.get(anchor.name, None)
        and not self.fallthroughs_map.get(anchor.name, [])):
      return True
    return False

  def _KwargsForAttribute(self, name, attribute, is_anchor=False):
    """Constructs the kwargs for adding an attribute to argparse."""
    # Argument is modal if it's the anchor, unless there are fallthroughs.
    # If fallthroughs can ever be configured in the ResourceInfo object,
    # a more robust solution will be needed, e.g. a GetFallthroughsForAttribute
    # method.
    required = is_anchor and not self.fallthroughs_map.get(attribute.name, [])
    # Expand the help text.
    help_text = attribute.help_text.format(resource=self.resource_spec.name)
    plural = attribute == self.resource_spec.anchor and self.plural
    if attribute.completer:
      completer = attribute.completer
    elif not self.resource_spec.disable_auto_completers:
      completer = completers.CompleterForAttribute(
          self.resource_spec,
          attribute.name)
    else:
      completer = None
    kwargs_dict = {
        'help': help_text,
        'type': attribute.value_type,
        'completer': completer}
    if util.IsPositional(name):
      if plural and required:
        kwargs_dict.update({'nargs': '+'})
      # The following should not usually happen because anchor args are
      # required.
      elif plural and not required:
        kwargs_dict.update({'nargs': '*'})
      elif not required:
        kwargs_dict.update({'nargs': '?'})
    else:
      kwargs_dict.update({'metavar': util.MetavarFormat(name)})
      if required:
        kwargs_dict.update({'required': True})
      if plural:
        kwargs_dict.update({'type': arg_parsers.ArgList()})
    return kwargs_dict

  def _GetAttributeArg(self, attribute):
    """Creates argument for a specific attribute."""
    name = self.attribute_to_args_map.get(attribute.name, None)
    is_anchor = attribute == self.resource_spec.anchor
    # Return None for any false value.
    if not name:
      return None
    return base.Argument(
        name,
        **self._KwargsForAttribute(name, attribute,
                                   is_anchor=is_anchor))

  def GetAttributeArgs(self):
    """Generate args to add to the argument group."""
    args = []
    for attribute in self.resource_spec.attributes:
      arg = self._GetAttributeArg(attribute)
      if arg:
        args.append(arg)

    return args

  def AddToParser(self, parser):
    """Adds all attributes of the concept to argparse.

    Creates a group to hold all the attributes and adds an argument for each
    attribute. If the presentation spec is required, then the anchor attribute
    argument will be required.

    Args:
      parser: the parser for the Calliope command.
    """
    args = self.GetAttributeArgs()
    if not args:
      # Don't create the group if there are not going to be any args generated.
      return
    # If this spec is supposed to be added to a subgroup, that overrides the
    # provided parser.
    parser = self.group or parser

    resource_group = parser.add_group(
        help=self.GetGroupHelp(),
        required=self.args_required)
    for arg in args:
      arg.AddToParser(resource_group)

  def GetExampleArgList(self):
    """Returns a list of command line example arg strings for the concept."""
    args = self.GetAttributeArgs()
    examples = []
    for arg in args:
      if arg.name.startswith('--'):
        example = '{}=my-{}'.format(arg.name, arg.name[2:])
      else:
        example = 'my-{}'.format(arg.name.lower())
      examples.append(example)
    return examples

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
    fallthroughs_map = self.BuildFullFallthroughsMap()

    if not self.plural:
      try:
        return self.concept_spec.Initialize(
            deps_lib.Deps(fallthroughs_map, parsed_args=parsed_args))
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
        anchor_values = fallthrough.GetValue(parsed_args)
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
            fallthroughs_map, parsed_args=parsed_args)))
      return resources
    if self.allow_empty:
      return resources
    return self.concept_spec.Initialize(deps_lib.Deps(
        fallthroughs_map, parsed_args=parsed_args))

  def ClearCache(self):
    self._result = None
    self._result_computed = False

