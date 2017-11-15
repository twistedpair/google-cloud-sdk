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

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope.concepts import handlers
from googlecloudsdk.calliope.concepts import util


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
    if self.required != other.required:
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
  """

  def __init__(self, name, concept_spec, group_help, prefixes=True,
               required=False, flag_name_overrides=None):
    """Initializes a ResourcePresentationSpec.

    Args:
      name: str, the name of the main arg for the concept.
      concept_spec: googlecloudsdk.calliope.concepts.ConceptSpec, The spec that
        specifies the concept.
      group_help: str, the help text for the entire arg group.
      prefixes: bool, whether to use prefixes before the attribute flags, such
        as `--myresource-project`. Defaults to True.
      required: bool, whether the anchor argument should be required.
      flag_name_overrides: {str: str}, dict of attribute names to the desired
        flag name. To remove a flag altogether, use '' as its rename value.
    """
    self.name = name
    self._concept_spec = concept_spec
    self.group_help = group_help
    self.prefixes = prefixes
    self.required = required

    # Create a rename map for the attributes to their flags.
    self.attribute_to_args_map = {}
    self._skip_flags = []
    for i, attribute in enumerate(self.concept_spec.attributes):
      is_anchor = i == len(self.concept_spec.attributes) - 1
      name = self.GetFlagName(
          attribute.name, self.name, flag_name_overrides, prefixes,
          is_anchor=is_anchor)
      if name:
        self.attribute_to_args_map[attribute.name] = name
      else:
        self._skip_flags.append(attribute.name)

  @property
  def title(self):
    """The title of the arg group for the spec, in all caps with spaces."""
    name = self.name.upper()
    if not util.IsPositional(name):
      name = name[len(util.PREFIX):].replace('-', ' ')
    return '{}'.format(name)

  def GetInfo(self):
    """Creates a ConceptInfo object to hold dependencies.

    Returns:
      (handlers.ConceptInfo) the holder for the resource's dependencies.
    """
    fallthroughs_map = {attribute.name: attribute.fallthroughs
                        for attribute in self.concept_spec.attributes}
    return handlers.ConceptInfo(
        self.concept_spec,
        self.attribute_to_args_map,
        fallthroughs_map)

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

  def _KwargsForAttribute(self, name, attribute, required=False):
    """Constructs the kwargs for adding an attribute to argparse."""
    # If this is the only argument in the group, the help text should be the
    # "group" help.
    if len(filter(bool, self.attribute_to_args_map.values())) == 1:
      help_text = self.group_help
    else:
      # Expand the help text.
      help_text = attribute.help_text.format(resource=self.concept_spec.name)
    kwargs_dict = {
        'help': help_text,
        'type': attribute.value_type,
        'completer': attribute.completer}
    if util.IsPositional(name):
      if required:
        kwargs_dict.update({'nargs': 1})
    else:
      kwargs_dict.update({'metavar': util.MetavarFormat(name)})
      if required:
        kwargs_dict.update({'required': True})
    return kwargs_dict

  def _GetAttributeArg(self, attribute, required=False):
    """Creates argument for a specific attribute."""
    name = self.attribute_to_args_map.get(attribute.name, None)
    # Return None for any false value.
    if not name:
      return None
    return base.Argument(
        name,
        **self._KwargsForAttribute(name, attribute, required=required))

  def GetAttributeArgs(self):
    """Generate args to add to the argument group."""
    for attribute in self.concept_spec.attributes[:-1]:
      arg = self._GetAttributeArg(attribute)
      if arg:
        yield arg
    # If the group is optional, the anchor arg is "modal": it is required only
    # if another argument in the group is specified.
    arg = self._GetAttributeArg(
        self.concept_spec.anchor, required=True)
    if arg:
      yield arg

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
    group = parser.add_group(
        help=self.GetGroupHelp(),
        required=self.required)
    for arg in self.GetAttributeArgs():
      arg.AddToParser(group)

  @property
  def concept_spec(self):
    return self._concept_spec


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
                  flag_name_overrides=None):
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

    Returns:
      (googlecloudsdk.calliope.concepts.concept_parsers.ConceptParser) The fully
        initialized ConceptParser.
    """
    presentation_spec = ResourcePresentationSpec(
        name,
        resource_spec,
        group_help,
        prefixes=False,
        required=required,
        flag_name_overrides=flag_name_overrides or {})
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
    for a, arg_name in presentation_spec.attribute_to_args_map.iteritems():
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
    for spec_name, spec in self._specs.iteritems():
      self._runtime_handler.AddConcept(
          util.NormalizeFormat(spec_name), spec.concept_spec, spec.GetInfo())
      spec.AddConceptToParser(parser)
