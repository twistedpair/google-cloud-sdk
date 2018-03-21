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
"""Classes to define how concept args are added to argparse.

A PresentationSpec is used to define how a concept spec is presented in an
individual command, such as its help text. ResourcePresentationSpecs are
used for resource specs.

ConceptParsers are parsers used to manage the adding of all concept arguments
to a given command's argparse parser. The ConceptParser is created with a list
of all resources needed for the command, and they should be added all at once
during calliope's Args method.
"""

from __future__ import absolute_import
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope.concepts import handlers
from googlecloudsdk.calliope.concepts import util
from googlecloudsdk.command_lib.util.concepts import completers

import six
from six.moves import filter  # pylint: disable=redefined-builtin


class PresentationSpec(object):
  """Class that defines how concept arguments are presented in a command."""

  def AddConceptToParser(self, parser):
    """Adds all attribute args for the concept to argparse.

    Must be overridden in subclasses.

    Args:
      parser: the parser for the Calliope command.
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

  def GetGroupHelp(self):
    """Get the group help for the group defined by the presentation spec.

    Must be overridden in subclasses.

    Returns:
      (str) the help text.
    """
    raise NotImplementedError

  def GetInfo(self):
    """Creates a ConceptInfo object to hold dependencies.

    May configure the object with different or additional fallthroughs from the
    ones present in from the ones present in the ConceptSpec's attributes.

    Must be overridden in subclasses.

    Returns:
      (googlecloudsdk.calliope.concepts.handlers.ConceptInfo) the created
        object.
    """
    raise NotImplementedError

  @property
  def concept_spec(self):
    """The ConceptSpec associated with the PresentationSpec.

    Must be overridden in subclasses.

    Returns:
      (googlecloudsdk.calliope.concepts.ConceptSpec) the concept spec.
    """
    raise NotImplementedError

  def __eq__(self, other):
    if not isinstance(other, type(self)):
      return False
    if self.GetGroupHelp() != other.GetGroupHelp():
      return False
    if ([(arg.name, arg.kwargs) for arg in self.GetAttributeArgs()]
        != [(arg.name, arg.kwargs) for arg in other.GetAttributeArgs()]):
      return False
    return True


class ResourcePresentationSpec(PresentationSpec):
  """Class that defines how concept arguments are presented in a command.

  Attributes:
    name: str, the name of the main arg for the concept. Can be positional or
      flag style (UPPER_SNAKE_CASE or --lower-train-case).
    concept_spec: googlecloudsdk.calliope.concepts.ConceptSpec, The spec that
      specifies the concept.
    group_help: str, the help text for the entire arg group.
    prefixes: bool, whether to use prefixes before the attribute flags, such as
      `--myresource-project`.
    required: bool, whether the anchor argument should be required. If True, the
      command will fail at argparse time if the anchor argument isn't given.
    attribute_to_args_map: {str: str}, a map from attribute names to arg names.
    plural: bool, True if the resource will be parsed as a list, False
      otherwise.
  """

  def __init__(self, name, concept_spec, group_help, prefixes=False,
               required=False, flag_name_overrides=None, plural=False,
               group=None):
    """Initializes a ResourcePresentationSpec.

    Args:
      name: str, the name of the main arg for the concept.
      concept_spec: googlecloudsdk.calliope.concepts.ConceptSpec, The spec that
        specifies the concept.
      group_help: str, the help text for the entire arg group.
      prefixes: bool, whether to use prefixes before the attribute flags, such
        as `--myresource-project`.
      required: bool, whether the anchor argument should be required.
      flag_name_overrides: {str: str}, dict of attribute names to the desired
        flag name. To remove a flag altogether, use '' as its rename value.
      plural: bool, True if the resource will be parsed as a list, False
        otherwise.
      group: the parser or subparser for a Calliope command that the resource
        arguments should be added to. If not provided, will be added to the main
        parser.
    """
    self.name = name
    self._concept_spec = concept_spec
    self.group_help = group_help
    self.prefixes = prefixes
    self.required = required
    self.plural = plural
    self.group = group

    # Create a rename map for the attributes to their flags.
    self._attribute_to_args_map = {}
    self._skip_flags = []
    for i, attribute in enumerate(self._concept_spec.attributes):
      is_anchor = i == len(self._concept_spec.attributes) - 1
      name = self.GetFlagName(
          attribute.name, self.name, flag_name_overrides, prefixes,
          is_anchor=is_anchor)
      if name:
        self._attribute_to_args_map[attribute.name] = name
      else:
        self._skip_flags.append(attribute.name)

  @property
  def title(self):
    """The title of the arg group for the spec, in all caps with spaces."""
    name = self.name.upper()
    if not util.IsPositional(name):
      name = name[len(util.PREFIX):].replace('-', ' ')
    return '{}'.format(name)

  @property
  def concept_spec(self):
    return self._concept_spec

  @property
  def resource_spec(self):
    return self.concept_spec

  @property
  def attribute_to_args_map(self):
    return self._attribute_to_args_map

  @property
  def args_required(self):
    """True if the resource is required and any arguments have no fallthroughs.

    If fallthroughs can ever be configured in the ResourceInfo object,
    a more robust solution will be needed, e.g. a GetFallthroughsForAttribute
    method.

    Returns:
      bool, whether the argument group should be required.
    """
    if not self.required:
      return False
    for attribute in self.concept_spec.attributes:
      if not attribute.fallthroughs:
        return True
    return False

  def GetInfo(self):
    """Overrides.

    Returns:
      (handlers.ResourceInfo) the holder for the resource's dependencies.
    """
    fallthroughs_map = {attribute.name: attribute.fallthroughs
                        for attribute in self.concept_spec.attributes}
    allow_empty = not self.required
    return handlers.ResourceInfo(
        self.resource_spec,
        self.attribute_to_args_map,
        fallthroughs_map,
        plural=self.plural,
        allow_empty=allow_empty)

  @staticmethod
  def GetFlagName(attribute_name, resource_name, flag_name_overrides=None,
                  prefixes=False, is_anchor=False):
    """Gets the flag name for a given attribute name.

    Returns a flag name for an attribute, adding prefixes as necessary or using
    overrides if an override map is provided.

    Args:
      attribute_name: str, the name of the attribute to base the flag name on.
      resource_name: str, the name of the resource the attribute belongs to
        (e.g. '--instance').
      flag_name_overrides: {str: str}, a dict of attribute names to exact string
        of the flag name to use for the attribute. None if no overrides.
      prefixes: bool, whether to use the resource name as a prefix for the flag.
      is_anchor: bool, True if this it he anchor flag, False otherwise.

    Returns:
      (str) the name of the flag.
    """
    flag_name_overrides = flag_name_overrides or {}
    if attribute_name in flag_name_overrides:
      return flag_name_overrides.get(attribute_name)
    if attribute_name == 'project':
      return ''
    if is_anchor:
      return resource_name
    prefix = util.PREFIX
    if prefixes:
      if resource_name.startswith(util.PREFIX):
        prefix += resource_name[len(util.PREFIX):] + '-'
      else:
        prefix += resource_name.lower().replace('_', '-') + '-'
    return prefix + attribute_name

  def _KwargsForAttribute(self, name, attribute, is_anchor=False):
    """Constructs the kwargs for adding an attribute to argparse."""
    # Argument is modal if it's the anchor, unless there are fallthroughs.
    # If fallthroughs can ever be configured in the ResourceInfo object,
    # a more robust solution will be needed, e.g. a GetFallthroughsForAttribute
    # method.
    required = is_anchor and not attribute.fallthroughs
    # If this is the only argument in the group, the help text should be the
    # "group" help.
    if len(list(filter(bool, self.attribute_to_args_map.values()))) == 1:
      help_text = self.group_help
    else:
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

  def _GetAttributeArg(self, attribute, is_anchor=False):
    """Creates argument for a specific attribute."""
    name = self.attribute_to_args_map.get(attribute.name, None)
    # Return None for any false value.
    if not name:
      return None
    return base.Argument(
        name,
        **self._KwargsForAttribute(name, attribute, is_anchor=is_anchor))

  def GetAttributeArgs(self):
    """Generate args to add to the argument group."""
    args = []
    for attribute in self.resource_spec.attributes[:-1]:
      arg = self._GetAttributeArg(attribute)
      if arg:
        args.append(arg)
    # If the group is optional, the anchor arg is "modal": it is required only
    # if another argument in the group is specified.
    arg = self._GetAttributeArg(
        self.concept_spec.anchor, is_anchor=True)
    if arg:
      args.append(arg)

    return args

  def GetGroupHelp(self):
    """Build group help for the argument group."""
    description = ['{} - {} The arguments in this group can be used to specify '
                   'the attributes of this resource.'.format(self.title,
                                                             self.group_help)]
    if self._skip_flags:
      description.append('(NOTE) Some attributes are not given arguments in '
                         'this group but can be set in other ways.')
      for attr_name in self._skip_flags:
        hint = 'To set the [{}] attribute: {}.'.format(
            attr_name,
            '; '.join(self.GetInfo().GetHints(attr_name)))
        description.append(hint)
    return ' '.join(description)

  def AddConceptToParser(self, parser):
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

  def __eq__(self, other):
    if not super(ResourcePresentationSpec, self).__eq__(other):
      return False
    return self.required == other.required


class ConceptParser(object):
  """Class that handles adding concept specs to argparse."""

  def __init__(self, presentation_specs):
    """Initializes a concept holder.

    Args:
      presentation_specs: [PresentationSpec], a list of the specs for concepts
        to be added to the parser.

    Raises:
      ValueError: if two presentation specs have the same name or two specs
        contain positional arguments.
    """
    self._specs = {}
    self._all_args = []
    self._runtime_handler = handlers.RuntimeHandler()
    for spec in presentation_specs:
      self._AddSpec(spec)

  @classmethod
  def ForResource(cls, name, resource_spec, group_help, required=False,
                  flag_name_overrides=None, plural=False, prefixes=False,
                  group=None):
    """Constructs a ConceptParser for a single resource argument.

    Automatically sets prefixes to False.

    Args:
      name: str, the name of the main arg for the resource.
      resource_spec: googlecloudsdk.calliope.concepts.ResourceSpec, The spec
        that specifies the resource.
      group_help: str, the help text for the entire arg group.
      required: bool, whether the main argument should be required for the
        command.
      flag_name_overrides: {str: str}, dict of attribute names to the desired
        flag name. To remove a flag altogether, use '' as its rename value.
      plural: bool, True if the resource will be parsed as a list, False
        otherwise.
      prefixes: bool, True if flag names will be prefixed with the resource
        name, False otherwise. Should be False for all typical use cases.
      group: the parser or subparser for a Calliope command that the resource
        arguments should be added to. If not provided, will be added to the main
        parser.

    Returns:
      (googlecloudsdk.calliope.concepts.concept_parsers.ConceptParser) The fully
        initialized ConceptParser.
    """
    presentation_spec = ResourcePresentationSpec(
        name,
        resource_spec,
        group_help,
        required=required,
        flag_name_overrides=flag_name_overrides or {},
        plural=plural,
        prefixes=prefixes,
        group=group)
    return cls([presentation_spec])

  def _ArgNameMatches(self, name, other_name):
    """Checks if two argument names match in the namespace.

    RESOURCE_ARG and --resource-arg will match with each other, as well as exact
    matches.

    Args:
      name: the first argument name.
      other_name: the second argument name.

    Returns:
      (bool) True if the names match.
    """
    if util.NormalizeFormat(name) == util.NormalizeFormat(other_name):
      return True
    return False

  def _AddSpec(self, presentation_spec):
    """Adds a given presentation spec to the concept holder's spec registry.

    Args:
      presentation_spec: PresentationSpec, the spec to be added.

    Raises:
      ValueError: if two presentation specs have the same name, if two
        presentation specs are both positional, or if two args are going to
        overlap.
    """
    # Check for duplicate spec names.
    for spec_name in self._specs:
      if self._ArgNameMatches(spec_name, presentation_spec.name):
        raise ValueError('Attempted to add two concepts with the same name: '
                         '[{}, {}]'.format(spec_name, presentation_spec.name))
      if (util.IsPositional(spec_name) and
          util.IsPositional(presentation_spec.name)):
        raise ValueError('Attempted to add multiple concepts with positional '
                         'arguments: [{}, {}]'.format(spec_name,
                                                      presentation_spec.name))

    # Also check for duplicate attribute names.
    for a, arg_name in six.iteritems(presentation_spec.attribute_to_args_map):
      del a  # Unused.
      name = util.NormalizeFormat(arg_name)
      if name in self._all_args:
        raise ValueError('Attempted to add a duplicate argument name: [{}]'
                         .format(arg_name))
      self._all_args.append(name)

    self._specs[presentation_spec.name] = presentation_spec

  def AddToParser(self, parser):
    """Adds attribute args for all presentation specs to argparse.

    Args:
      parser: the parser for a Calliope command.
    """
    parser.add_concepts(self._runtime_handler)
    for spec_name, spec in six.iteritems(self._specs):
      self._runtime_handler.AddConcept(
          util.NormalizeFormat(spec_name), spec.GetInfo(),
          required=spec.required)
      spec.AddConceptToParser(parser)

  def GetExampleArgString(self):
    """Returns a command line example arg string for the concept."""
    examples = []
    for _, spec in six.iteritems(self._specs):
      args = spec.GetExampleArgList()
      if args:
        examples.extend(args)

    def _PositionalsFirst(arg):
      prefix = 'Z' if arg.startswith('--') else 'A'
      return prefix + arg

    return ' '.join(sorted(examples, key=_PositionalsFirst))
