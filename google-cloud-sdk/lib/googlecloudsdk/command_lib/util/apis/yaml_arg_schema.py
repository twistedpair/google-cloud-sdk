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

"""Helpers for loading resource argument definitions from a yaml declaration."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc
import itertools

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import multitype
from googlecloudsdk.calliope.concepts import util as resource_util
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.command_lib.util.apis import registry
from googlecloudsdk.command_lib.util.apis import update_args
from googlecloudsdk.command_lib.util.apis import update_resource_args
from googlecloudsdk.command_lib.util.apis import yaml_command_schema_util as util
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs
from googlecloudsdk.core.util import text


class Arguments(object):
  """Everything about cli arguments are registered in this section."""

  def __init__(self, data, request_data=None):
    self.additional_arguments_hook = util.Hook.FromData(
        data, 'additional_arguments_hook')

    params_data = data.get('params', [])
    params_data.extend(self._GetResourceData(data, request_data))

    request_data = request_data or {}
    self.params = [
        YAMLArgument.FromData(param_data, request_data.get('api_version'))
        for param_data in params_data]

    self.labels = Labels(data.get('labels')) if data.get('labels') else None
    self.exclude = data.get('exclude', [])

  # TODO(b/272076207): remove method after surfaces are updated with new schema
  def _GetResourceData(self, data, request_data):
    """Gets the resource data from the arguments and request data.

    This a temporary method to align the old and new schemas and should be
    removed after b/272076207 is complete.

    Args:
      data: arguments yaml data in command.
      request_data: request yaml data in command.

    Returns:
      resource data with missing request params.

    Raises:
      InvalidSchemaError: if the YAML command is malformed.
    """
    request_data = request_data or {}

    resource = data.get('resource')
    if not resource:
      return []

    # Updates resource data with the new schema.
    moved_request_params = [
        'resource_method_params',
        'parse_resource_into_request',
        'use_relative_name',
    ]
    for request_param in moved_request_params:
      param = request_data.get(request_param)
      if param is not None:
        if resource.get(request_param) is not None:
          raise util.InvalidSchemaError(
              '[{}] is defined in both request and argument.param. Recommend '
              'only defining in argument.param'.format(request_param))
        resource[request_param] = param

    # Update spec attribute to resource_spec attribute.
    resource['resource_spec'] = resource.get('spec', {})

    return [resource]


class Labels(object):
  """Everything about labels of GCP resources."""

  def __init__(self, data):
    self.api_field = data['api_field']


class YAMLArgument(object, metaclass=abc.ABCMeta):
  """Root for generating all arguments from yaml data.

  Requires all subclasses to contain Generate and Parse methods.
  """

  @classmethod
  def FromData(cls, data, api_version=None):
    group = data.get('group')
    if group:
      return ArgumentGroup.FromData(group, api_version)

    if data.get('resource_spec'):
      return YAMLConceptArgument.FromData(data, api_version)

    return Argument.FromData(data)

  @property
  @abc.abstractmethod
  def api_fields(self):
    """List of api fields this argument maps to."""

  @abc.abstractmethod
  def IsApiFieldSpecified(self, namespace):
    """Whether the argument with an api field is specified in the namespace."""

  @abc.abstractmethod
  def Generate(self, methods, shared_resource_flags):
    """Generates and returns the base argument."""

  @abc.abstractmethod
  def Parse(self, method, message, namespace, group_required):
    """Parses namespace for argument's value and appends value to req message."""


def _IsSpecified(namespace, arg_dest, clearable=False):
  """Provides whether or not the argument has been specified.

  Args:
    namespace: user specified arguments
    arg_dest: str, normalize string of the argument name
    clearable: Boolean, True if param has clearable arguments
      such as clear, add, etc

  Returns:
    Boolean, whether or not the argument is specified in the namespace
  """
  specified_args_list = set(
      resource_util.NormalizeFormat(key)
      for key in namespace.GetSpecifiedArgs().keys())

  dest = arg_dest and resource_util.NormalizeFormat(arg_dest)
  if dest in specified_args_list:
    return True

  if clearable:
    update_prefixes = (prefix.value for prefix in update_args.Prefix)
  else:
    update_prefixes = ()
  negative_prefixes = ('no',)

  for prefix in itertools.chain(update_prefixes, negative_prefixes):
    if '{}_{}'.format(prefix, dest) in specified_args_list:
      return True
  else:
    return False


class ArgumentGroup(YAMLArgument):
  """Encapsulates data used to generate argument groups.

  Most of the attributes of this object correspond directly to the schema and
  have more complete docs there.

  Attributes:
    help_text: Optional help text for the group.
    required: True to make the group required.
    mutex: True to make the group mutually exclusive.
    hidden: True to make the group hidden.
    arg_name: The name of the argument that will be generated.
    clearable: True to automatically generate update flags such as `clear`
    settable: True to automatically generate arg_object flag to set the value
      of the whole argument argument group.
    arguments: The list of arguments in the group.
  """

  @classmethod
  def FromData(cls, data, api_version=None):
    """Gets the arg group definition from the spec data.

    Args:
      data: The group spec data.
      api_version: Request method api version.

    Returns:
      ArgumentGroup, the parsed argument group.

    Raises:
      InvalidSchemaError: if the YAML command is malformed.
    """
    if data.get('settable', False):
      settable_arg = SettableArgumentForGroup.FromData(data)
    else:
      settable_arg = None

    if data.get('clearable', False):
      clearable_arg = ClearableArgumentForGroup.FromData(data)
    else:
      clearable_arg = None

    return cls(
        help_text=data.get('help_text'),
        required=data.get('required', False),
        mutex=data.get('mutex', False),
        hidden=data.get('hidden', False),
        api_field=data.get('api_field'),
        arg_name=data.get('arg_name'),
        arguments=[YAMLArgument.FromData(item, api_version)
                   for item in data.get('params')],
        settable_arg=settable_arg,
        clearable_arg=clearable_arg,
    )

  def __init__(self, help_text=None, required=False, mutex=False, hidden=False,
               api_field=None, arg_name=None,
               arguments=None, settable_arg=None, clearable_arg=None):
    super(ArgumentGroup, self).__init__()
    self.help_text = help_text
    self.required = required
    self.mutex = mutex
    self.hidden = hidden
    self.arg_name = arg_name
    self.arguments = arguments
    self._settable_arg = settable_arg
    self._clearable_arg = clearable_arg
    self._api_field = api_field

  @property
  def api_fields(self):
    api_fields = []
    for arg in self.arguments:
      api_fields.extend(arg.api_fields)
    return api_fields

  @property
  def parent_api_field(self):
    """Returns api field that is the parent of all api fields in the group."""
    if self._api_field:
      return self._api_field
    else:
      return arg_utils.GetSharedParent(self.api_fields)

  def _SettableIsSpecified(self, namespace):
    return (arg := self._settable_arg) and arg.IsApiFieldSpecified(namespace)

  def _ClearableIsSpecified(self, namespace):
    return (arg := self._clearable_arg) and arg.IsApiFieldSpecified(namespace)

  def IsApiFieldSpecified(self, namespace):
    if (self._SettableIsSpecified(namespace) or
        self._ClearableIsSpecified(namespace)):
      return True

    for arg in self.arguments:
      if arg.IsApiFieldSpecified(namespace):
        return True
    else:
      return False

  def _GenerateClearFlag(self, methods, shared_resource_flags):
    """Returns the clear flag for the argument group if specified."""
    return (self._clearable_arg and
            self._clearable_arg.Generate(methods, shared_resource_flags))

  def _GenerateSetFlag(self, methods, shared_resource_flags):
    """Returns the set flag for the argument group if specified."""
    return (self._settable_arg and
            self._settable_arg.Generate(methods, shared_resource_flags))

  def _GenerateMutexGroup(self, base_group, set_flag):
    """Returns the mutex group for the argument group if specified."""
    arg_names = (
        arg.arg_name for arg in self.arguments if isinstance(arg, Argument))

    mutex_group = base.ArgumentGroup(
        mutex=True,
        required=self.required,
        hidden=self.hidden,
        help=(
            f'Set the value of {self._api_field} by using flag '
            f'[{self._settable_arg.arg_name}] or flags '
            f'[{", ".join(arg_names)}].'),
    )
    mutex_group.AddArgument(base_group)
    mutex_group.AddArgument(set_flag)
    return mutex_group

  def Generate(self, methods, shared_resource_flags=None):
    """Generates and returns the base argument group.

    Args:
      methods: list[registry.APIMethod], used to generate other arguments
      shared_resource_flags: [string], list of flags being generated elsewhere

    Returns:
      The base argument group.
    """
    base_group = base.ArgumentGroup(
        mutex=self.mutex, required=self.required, help=self.help_text,
        hidden=self.hidden)
    # Add arguments in group
    for arg in self.arguments:
      base_group.AddArgument(arg.Generate(methods, shared_resource_flags))

    # Add clearable flag
    if clear_flag := self._GenerateClearFlag(methods, shared_resource_flags):
      base_group.AddArgument(clear_flag)

    # Add settable flag
    if set_flag := self._GenerateSetFlag(methods, shared_resource_flags):
      if base_group.arguments:
        return self._GenerateMutexGroup(base_group, set_flag)
      else:
        return set_flag
    else:
      return base_group

  def Parse(self, method, message, namespace, group_required=True):
    """Sets argument group message values, if any, from the parsed args.

    Args:
      method: registry.APIMethod, used to parse sub arguments.
      message: The API message, None for non-resource args.
      namespace: The parsed command line argument namespace.
      group_required: bool, if true, then parent argument group is required
    """
    arg_utils.ClearUnspecifiedMutexFields(message, namespace, self)

    # Remove values
    if self._clearable_arg:
      self._clearable_arg.Parse(method, message, namespace, group_required)

    # Add values
    if self._settable_arg:
      self._settable_arg.Parse(method, message, namespace, group_required)

    for arg in self.arguments:
      arg.Parse(method, message, namespace, group_required and self.required)


class Argument(YAMLArgument):
  """Encapsulates data used to generate arguments.

  Most of the attributes of this object correspond directly to the schema and
  have more complete docs there.

  Attributes:
    api_field: The name of the field in the request that this argument values
      goes.
    disable_unused_arg_check: Disables yaml_command_test check for unused
      arguments in static analysis.
    arg_name: The name of the argument that will be generated. Defaults to the
      api_field if not set.
    help_text: The help text for the generated argument.
    metavar: The metavar for the generated argument. This will be generated
      automatically if not provided.
    completer: A completer for this argument.
    is_positional: Whether to make the argument positional or a flag.
    type: The type to use on the argparse argument.
    choices: A static map of choice to value the user types.
    default: The default for the argument.
    fallback: A function to call and use as the default for the argument.
    processor: A function to call to process the value of the argument before
      inserting it into the request.
    required: True to make this a required flag.
    hidden: True to make the argument hidden.
    action: An override for the argparse action to use for this argument.
    repeated: False to accept only one value when the request field is actually
      repeated.
    generate: False to not generate this argument. This can be used to create
      placeholder arg specs for defaults that don't actually need to be
      generated.
    clearable: True to automatically generate update flags such as `clear`,
      `update`, `remove`, and `add`
  """

  @classmethod
  def FromData(cls, data):
    """Gets the arg definition from the spec data.

    Args:
      data: The spec data.

    Returns:
      Argument, the parsed argument.

    Raises:
      InvalidSchemaError: if the YAML command is malformed.
    """
    api_field = data.get('api_field')
    disable_unused_arg_check = data.get('disable_unused_arg_check')
    arg_name = data.get('arg_name', api_field)
    if not arg_name:
      raise util.InvalidSchemaError(
          'An argument must have at least one of [api_field, arg_name].')
    is_positional = data.get('is_positional')
    flag_name = arg_name if is_positional else '--' + arg_name

    if data.get('default') and data.get('fallback'):
      raise util.InvalidSchemaError(
          'An argument may have at most one of [default, fallback].')

    try:
      help_text = data['help_text']
    except KeyError:
      raise util.InvalidSchemaError('An argument must have help_text.')

    choices = data.get('choices')

    return cls(
        api_field=api_field,
        arg_name=arg_name,
        help_text=help_text,
        metavar=data.get('metavar'),
        completer=util.Hook.FromData(data, 'completer'),
        is_positional=is_positional,
        type=util.ParseType(data),
        choices=[util.Choice(d) for d in choices] if choices else None,
        default=data.get('default', arg_utils.UNSPECIFIED),
        fallback=util.Hook.FromData(data, 'fallback'),
        processor=util.Hook.FromData(data, 'processor'),
        required=data.get('required', False),
        hidden=data.get('hidden', False),
        action=util.ParseAction(data.get('action'), flag_name),
        repeated=data.get('repeated'),
        disable_unused_arg_check=disable_unused_arg_check,
        clearable=data.get('clearable', False),
    )

  # pylint:disable=redefined-builtin, type param needs to match the schema.
  def __init__(self,
               api_field=None,
               arg_name=None,
               help_text=None,
               metavar=None,
               completer=None,
               is_positional=None,
               type=None,
               choices=None,
               default=arg_utils.UNSPECIFIED,
               fallback=None,
               processor=None,
               required=False,
               hidden=False,
               action=None,
               repeated=None,
               generate=True,
               disable_unused_arg_check=False,
               clearable=False):
    super(Argument, self).__init__()
    self.api_field = api_field
    self.disable_unused_arg_check = disable_unused_arg_check
    self.arg_name = arg_name
    self.help_text = help_text
    self.metavar = metavar
    self.completer = completer
    self.is_positional = is_positional
    self.type = type
    self.choices = choices
    self.default = default
    self.fallback = fallback
    self.processor = processor
    self.required = required
    self.hidden = hidden
    self.action = action
    self.repeated = repeated
    self.generate = generate
    self.clearable = clearable

  @property
  def api_fields(self):
    return [self.api_field] if self.api_field else []

  def IsApiFieldSpecified(self, namespace):
    if not self.api_fields:
      return False
    return _IsSpecified(
        namespace=namespace,
        arg_dest=resource_util.NormalizeFormat(self.arg_name),
        clearable=self.clearable)

  def _GetField(self, message):
    """Gets apitools field associated with api_field."""
    if message and self.api_field:
      return arg_utils.GetFieldFromMessage(message, self.api_field)
    else:
      return None

  def _GetFieldFromMethods(self, methods):
    """Gets apitools field associated with api_field from methods."""
    if not methods or not self.api_field:
      return None

    field = self._GetField(methods[0].GetRequestType())

    for method in methods:
      other_field = self._GetField(method.GetRequestType())
      if (field.name != other_field.name or
          field.variant != other_field.variant or
          field.repeated != other_field.repeated):
        message_names = ', '.join(
            method.GetRequestType().__name__ for method in methods)
        raise util.InvalidSchemaError(
            f'Unable to generate flag for api field {self.api_field}. '
            f'Found non equivalent fields in messages: [{message_names}].')

    return field

  def _GenerateUpdateFlags(self, field):
    """Creates update flags generator using aptiools field."""
    return update_args.UpdateBasicArgumentGenerator.FromArgData(self, field)

  def _ParseUpdateArgsFromNamespace(self, namespace, message):
    """Parses update flags and returns modified apitools message field."""
    field = self._GetField(message)
    return self._GenerateUpdateFlags(field).Parse(namespace, message)

  def Generate(self, methods, shared_resource_flags=None):
    """Generates and returns the base argument.

    Args:
      methods: list[registry.APIMethod], used to generate other arguments.
      shared_resource_flags: [string], list of flags being generated elsewhere.

    Returns:
      The base argument.
    """
    field = self._GetFieldFromMethods(methods)

    if self.clearable and field:
      return self._GenerateUpdateFlags(field).Generate()
    else:
      return arg_utils.GenerateFlag(field, self)

  def Parse(self, method, message, namespace, group_required=True):
    """Sets the argument message value, if any, from the parsed args.

    Args:
      method: registry.APIMethod, used to parse other arguments.
      message: The API message, None for non-resource args.
      namespace: The parsed command line argument namespace.
      group_required: bool, whether parent argument group is required.
        Unused here.
    """
    del method, group_required  # unused params
    if self.api_field is None:
      return

    if self.clearable:
      value = self._ParseUpdateArgsFromNamespace(namespace, message)
      if self.IsApiFieldSpecified(namespace):
        arg_utils.SetFieldInMessage(message, self.api_field, value)
      return

    value = arg_utils.GetFromNamespace(
        namespace, self.arg_name, fallback=self.fallback)
    if value is None:
      return

    field = self._GetField(message)
    value = arg_utils.ConvertValue(
        field, value, repeated=self.repeated, processor=self.processor,
        choices=util.Choice.ToChoiceMap(self.choices))

    arg_utils.SetFieldInMessage(message, self.api_field, value)


class SettableArgumentForGroup(Argument):
  """Encapsulates data used to generate arg_object flag for argument group."""

  @classmethod
  def FromData(cls, data):
    """Gets the arg group definition from the spec data."""
    try:
      api_field = data['api_field']
      arg_name = data['arg_name']
    except KeyError:
      raise util.InvalidSchemaError(
          'Settable argument group must have api_field and arg_name set.')

    return cls(
        api_field=api_field,
        arg_name=arg_name,
        help_text=data.get('help_text'),
        required=data.get('required', False),
        hidden=data.get('hidden', False),
        arg_type=util.ArgObject.FromData(data, disable_key_description=True),
    )

  def __init__(self, api_field, arg_name, help_text=None, required=False,
               hidden=False, arg_type=None):
    super(SettableArgumentForGroup, self).__init__(
        api_field=api_field,
        arg_name=arg_name,
        help_text=help_text,
        required=required,
        hidden=hidden,
        type=arg_type,
    )


class ClearableArgumentForGroup(Argument):
  """Encapsulates data used to generate a clearable flag.

  Clearable flag is specifically for clearing a message field corresponding to
  the argument group.
  """

  @classmethod
  def FromData(cls, data):
    """Gets the arg group definition from the spec data."""
    try:
      api_field = data['api_field']
      arg_name = data['arg_name']
    except KeyError:
      raise util.InvalidSchemaError(
          'Clearable argument group must have api_field and arg_name set.')

    return cls(
        api_field=api_field,
        arg_name=arg_name,
        required=False,
        hidden=data.get('hidden', False),
    )

  def __init__(self, api_field, arg_name, required=False, hidden=False):
    super(ClearableArgumentForGroup, self).__init__(
        api_field=api_field,
        arg_name='-'.join(
            (update_args.Prefix.CLEAR.value,
             resource_util.KebabCase(arg_name))),
        help_text=f'Set {api_field} back to default value.',
        required=required,
        hidden=hidden,
        type=bool,
    )

  def Parse(self, method, message, namespace, group_required=True):
    if arg_utils.GetFromNamespace(namespace, self.arg_name):
      arg_utils.ResetFieldInMessage(message, self.api_field)


def _GetAttributeNames(resource_spec):
  return [attr.name for attr in resource_spec.attributes]


def _GetAnchors(resource_spec):
  """Get the anchor for the resource arg."""
  return [a for a in resource_spec.attributes
          if resource_spec.IsLeafAnchor(a)]


def _IsAnchorSpecified(
    resource_spec, namespace, attribute_to_dest_map,
    presentation_name, clearable):
  """Checks if any of the resource anchors are specified in the namespace."""
  # Determines when whole resource is cleared.
  if _IsSpecified(namespace, presentation_name, clearable):
    return True

  # Determines when individual anchors are specified or cleared.
  for anchor in _GetAnchors(resource_spec):
    arg_name = attribute_to_dest_map.get(anchor.name)
    if _IsSpecified(namespace, arg_name, clearable):
      return True
  return False


def _GetPresentationName(resource_spec, repeated):
  """Name of the resource arg.

  Name is used to prefix attribute flags (if needed) and determine the
  location where the resource is specified in the namespace.

  For presentation name foo-bar, the expected format is...
    1. `foo-bar` if anchor is not positional
    2. `FOO_BAR` if anchor is positional

  Args:
    resource_spec: The resource spec.
    repeated: True if the resource is repeated.

  Returns:
    The name of the resource arg.
  """
  count = 2 if repeated else 1
  # Only non-positional resources can have multiple anchors.
  name = '-or-'.join(a.name for a in _GetAnchors(resource_spec))
  return text.Pluralize(count, name)


def _GetIsList(methods):
  is_list = set(method.IsList() for method in methods)
  if len(is_list) > 1:
    raise util.InvalidSchemaError(
        'Methods used to generate YAMLConceptArgument cannot contain both '
        'list and non-list methods. Update the list of methods to only use '
        'list or non-list methods.')

  if is_list:
    return is_list.pop()
  else:
    return False


def _GetResourceMap(ref, resource_method_params):
  """Generates a map of message fields to respective resource attribute value.

    Ex: If you have a resource arg...
      projects/foo/locations/us-central1/instances/bar

    ...and you want to set the `parent` field in the request message to the
    resource's relative name, you would use this function like...
      _GetResourceMap(ref, {'parent': '__relative_name__'})

    ...and it would return...
      {'parent': 'projects/foo/locations/us-central1/instances/bar'}

  Args:
    ref: Parsed resource arg.
    resource_method_params: A dict of message field name to resource attribute
      name.

  Returns:
    A dict of message field name to resource attribute value.
  """
  message_resource_map = {}
  for message_field_name, param_str in resource_method_params.items():
    if ref is None:
      values = None
    elif isinstance(ref, list):
      values = [util.FormatResourceAttrStr(param_str, r) for r in ref]
    else:
      values = util.FormatResourceAttrStr(param_str, ref)
    message_resource_map[message_field_name] = values
  return message_resource_map


def _FallthroughFlagFromData(fallthrough_data):
  """Returns the fallthrough string for the given fallthrough data."""
  if fallthrough_data.get('is_positional', False):
    return resource_util.PositionalFormat(fallthrough_data['arg_name'])
  else:
    return resource_util.FlagNameFormat(fallthrough_data['arg_name'])


def _GenerateFallthroughsMapFromData(fallthroughs_data):
  """Generate a map of command-level fallthroughs from yaml data."""
  command_level_fallthroughs = {}

  for attr_name, fallthroughs_data in (fallthroughs_data or {}).items():
    fallthroughs_list = [_FallthroughFlagFromData(fallthrough)
                         for fallthrough in fallthroughs_data]
    command_level_fallthroughs[attr_name] = fallthroughs_list

  return command_level_fallthroughs


def _GenerateFullFallthroughsMap(
    arg_fallthroughs, attribute_to_flag_map,
    shared_resource_flags, presentation_flag_name):
  """Generate a map of fallthroughs for the given argument.

  Generates a map of a resource attribute name and the flag it should default
  to for the ConceptParser. The shared (ignored) flags have to be added
  manually since they are not added by the ConceptParser.

  Args:
    arg_fallthroughs: A dict of fallthroughs for the given argument.
    attribute_to_flag_map: The names of the attributes in the
      resource spec.
    shared_resource_flags: Flags that are already generated elsewhere.
    presentation_flag_name: The name of the anchor argument.

  Returns:
    A dictionary of resource attributes to fallthrough flags
  """
  shared = shared_resource_flags or []
  command_level_fallthroughs = {}
  full_arg_fallthroughs = arg_fallthroughs.copy()
  full_arg_fallthroughs.update({
      attr: [resource_util.FlagNameFormat(flag)]
      for attr, flag in attribute_to_flag_map.items() if flag in shared
  })

  concept_parsers.UpdateFallthroughsMap(
      command_level_fallthroughs, presentation_flag_name, full_arg_fallthroughs)
  return command_level_fallthroughs


def _GenerateIgnoredFlagsMap(
    shared_resource_flags, ignored_flags, attribute_to_flag_map):
  """Generate a map of flags that should be ignored.

  Flags are either ignored because they have already been generated elsewhere
  or because the command explicitly removed them.

  Args:
    shared_resource_flags: Flags that are already generated elsewhere
    ignored_flags: Flags that have been explicitly removed in the command
    attribute_to_flag_map: Attributes mapped to flag names

  Returns:
    A map of flags to ignore to an empty string.
  """
  all_ignored_flags = ignored_flags + (shared_resource_flags or [])
  return {
      attr: '' for attr, flag in attribute_to_flag_map.items()
      if flag in all_ignored_flags
  }


def _AllRemovedFlags(removed_attrs, atribute_to_flag_map):
  """Returns all the flags that need to be removed."""
  ignored = list(set(
      resource_util.FlagNameFormat(flag)
      for flag in concepts.IGNORED_FIELDS.values()))
  removed_flags = [
      atribute_to_flag_map[attr] for attr in removed_attrs
      if attr in atribute_to_flag_map]
  return ignored + removed_flags


class YAMLConceptArgument(YAMLArgument, metaclass=abc.ABCMeta):
  """Encapsulate data used to generate and parse all resource args.

  YAMLConceptArgument is parent class that parses data and standardizes
  the interface (abstract base class) for YAML resource arguments by
  requiring methods Generate, Parse, and ParseResourceArg. All of the
  methods on YAMLConceptArgument are private helper methods for YAML
  resource arguments to share minor logic.
  """

  @classmethod
  def FromData(cls, data, api_version=None):
    if not data:
      return None

    resource_spec = data['resource_spec']
    help_text = data['help_text']
    kwargs = {
        'is_positional': data.get('is_positional'),
        'is_parent_resource': data.get('is_parent_resource', False),
        'is_primary_resource': data.get('is_primary_resource'),
        'removed_flags': data.get('removed_flags'),
        'arg_name': data.get('arg_name'),
        'command_level_fallthroughs': data.get(
            'command_level_fallthroughs', {}),
        'display_name_hook': data.get('display_name_hook'),
        'request_id_field': data.get('request_id_field'),
        'resource_method_params': data.get('resource_method_params', {}),
        'parse_resource_into_request': data.get(
            'parse_resource_into_request', True),
        'use_relative_name': data.get('use_relative_name', True),
        'override_resource_collection': data.get(
            'override_resource_collection', False),
        'required': data.get('required'),
        'repeated': data.get('repeated', False),
        'request_api_version': api_version,
        'clearable': data.get('clearable', False),
    }

    if 'resources' in data['resource_spec']:
      return YAMLMultitypeResourceArgument(resource_spec, help_text, **kwargs)
    else:
      return YAMLResourceArgument(resource_spec, help_text, **kwargs)

  def __init__(self, data, group_help, is_positional=None, removed_flags=None,
               is_parent_resource=False, is_primary_resource=None,
               arg_name=None, command_level_fallthroughs=None,
               display_name_hook=None, request_id_field=None,
               resource_method_params=None, parse_resource_into_request=True,
               use_relative_name=True, override_resource_collection=False,
               required=None, repeated=False, clearable=False, **unused_kwargs):
    self.flag_name_override = arg_name
    self.group_help = group_help
    self._is_positional = is_positional
    self.is_parent_resource = is_parent_resource
    self.is_primary_resource = is_primary_resource
    self._removed_attrs = removed_flags or []
    self.command_level_fallthroughs = _GenerateFallthroughsMapFromData(
        command_level_fallthroughs)
    # TODO(b/274890004): Remove data.get('request_id_field')
    self.request_id_field = request_id_field or data.get('request_id_field')
    self.resource_method_params = resource_method_params or {}
    self.parse_resource_into_request = parse_resource_into_request
    self.use_relative_name = use_relative_name
    self.override_resource_collection = override_resource_collection
    self._required = required
    self.repeated = repeated
    self.clearable = clearable

    # All resource spec types have these values
    self.name = data['name']
    self._plural_name = data.get('plural_name')

    self.display_name_hook = (
        util.Hook.FromPath(display_name_hook) if display_name_hook else None)

  @property
  @abc.abstractmethod
  def collection(self):
    """"Get registry.APICollection based on collection and api_version."""
    pass

  @property
  @abc.abstractmethod
  def collections(self):
    """Get registry.APICollection based on collection and api_version."""
    pass

  @property
  @abc.abstractmethod
  def anchors(self):
    """Get the anchors from the resource spec."""
    pass

  @property
  @abc.abstractmethod
  def multitype(self):
    """Whether the resource arg is multitype."""
    pass

  @property
  @abc.abstractmethod
  def attribute_names(self):
    """Names of attributes in the resource spec."""
    pass

  @property
  @abc.abstractmethod
  def attribute_to_flag_map(self):
    """Returns a map of attribute name to normalized flag name."""
    pass

  @property
  @abc.abstractmethod
  def ignored_flags(self):
    """Returns a map of attribute name to normalized flag name."""
    pass

  @abc.abstractmethod
  def IsPrimaryResource(self, resource_collection):
    """Determines if this resource arg is the primary resource."""
    pass

  @abc.abstractmethod
  def GenerateResourceArg(
      self, method, presentation_flag_name=None, flag_name_override=None,
      shared_resource_flags=None, group_help=None):
    """Generate the resource arg for the given method."""
    pass

  @abc.abstractmethod
  def ParseResourceArg(self, namespace, group_required=True):
    """Parses the resource ref from namespace (no update flags)."""
    pass

  @abc.abstractmethod
  def GetPresentationFlagName(self, resource_collection, is_list_method):
    """Get the anchor argument name for the resource spec."""
    pass

  @property
  def api_fields(self):
    """Where the resource arg is mapped into the request message."""
    if self.resource_method_params:
      return list(self.resource_method_params.keys())
    else:
      return []

  def IsPositional(self, resource_collection=None, is_list_method=False):
    """Determines if the resource arg is positional.

    Args:
      resource_collection: APICollection | None, collection associated with
        the api method. None if a methodless command.
      is_list_method: bool | None, whether command is associated with list
        method. None if methodless command.

    Returns:
      bool, whether the resource arg anchor is positional
    """
    # If left unspecified, decide whether the resource is positional based on
    # whether the resource is primary.
    if self._is_positional is not None:
      return self._is_positional

    is_primary_resource = self.IsPrimaryResource(resource_collection)
    return is_primary_resource and not is_list_method

  def IsRequired(self, resource_collection=None):
    """Determines if the resource arg is required.

    Args:
      resource_collection: APICollection | None, collection associated with
        the api method. None if a methodless command.

    Returns:
      bool, whether the resource arg is required
    """
    if self._required is not None:
      return self._required

    return self.IsPrimaryResource(resource_collection)

  def _GetMethodCollection(self, methods):
    for method in methods:
      if self.IsPrimaryResource(method.resource_argument_collection):
        return method.resource_argument_collection
    else:
      # Return any of the methods if none are associated with
      # a primary collection
      return methods[0].resource_argument_collection if methods else None


class YAMLResourceArgument(YAMLConceptArgument):
  """Encapsulates the spec for the resource arg of a declarative command."""

  @classmethod
  def FromSpecData(cls, data, request_api_version, **kwargs):
    """Create a resource argument with no command-level information configured.

    Given just the reusable resource specification (such as attribute names
    and fallthroughs, it can be used to generate a ResourceSpec. Not suitable
    for adding directly to a command as a solo argument.

    Args:
      data: the yaml resource definition.
      request_api_version: str, api version of request collection.
      **kwargs: attributes outside of the resource spec

    Returns:
      YAMLResourceArgument with no group help or flag name information.
    """
    if not data:
      return None

    return cls(data, None, request_api_version=request_api_version, **kwargs)

  def __init__(self, data, group_help, request_api_version=None, **kwargs):
    super(YAMLResourceArgument, self).__init__(data, group_help, **kwargs)

    self._full_collection_name = data['collection']
    # TODO(b/273778771): Defaulting to the request's api version is a temporary
    # work around. We should avoid mutating the YAML data directly.
    # However, because the resource api version can be None, the APICollection
    # gathered from request.method can be different from the
    # APICollection.api_version generated YAMLResourceArgument.collection.
    # Passing in method resource_collection was supposed to just validate the
    # resource spec but it was also defaulting the api version.
    self._api_version = data.get('api_version', request_api_version)
    self.attribute_data = data['attributes']
    self._disable_auto_completers = data.get('disable_auto_completers', True)

    for removed in self._removed_attrs:
      if removed not in self.attribute_names:
        raise util.InvalidSchemaError(
            'Removed flag [{}] for resource arg [{}] references an attribute '
            'that does not exist. Valid attributes are [{}]'.format(
                removed, self.name, ', '.join(self.attribute_names)))

  @property
  def collection(self):
    return registry.GetAPICollection(
        self._full_collection_name, api_version=self._api_version)

  @property
  def collections(self):
    return [self.collection]

  @property
  def multitype(self):
    return False

  @property
  def anchors(self):
    return _GetAnchors(self._resource_spec)

  @property
  def attribute_names(self):
    return _GetAttributeNames(self._resource_spec)

  @property
  def _resource_spec(self):
    """Resource spec generated from the YAML."""

    # If attributes do not match resource_collection.detailed_params, will
    # raise InvalidSchema error
    attributes = concepts.ParseAttributesFromData(
        self.attribute_data, self.collection.detailed_params)

    return concepts.ResourceSpec(
        self.collection.full_name,
        resource_name=self.name,
        api_version=self.collection.api_version,
        disable_auto_completers=self._disable_auto_completers,
        plural_name=self._plural_name,
        # TODO(b/297860320): is_positional should be self.IsPositional(method)
        # in order to automatically change underscores to hyphens
        # and vice versa. However, some surfaces will break if we change
        # it now.
        is_positional=self._is_positional,
        **{attribute.parameter_name: attribute for attribute in attributes})

  @property
  def presentation_name(self):
    # To get the correct casing (how it should appear on the command line)
    # use GetPresentationFlagName
    if self.flag_name_override:
      return self.flag_name_override
    else:
      return _GetPresentationName(self._resource_spec, self.repeated)

  @property
  def attribute_to_flag_map(self):
    """Returns a map of attribute name to flag name."""
    # Not an accurate attribute to flag name map since it does not include
    # positional vs non-positional or skipped flags. However, it is sufficient
    # for the purposes of determining if a flag is specified.
    return self._GeneratePresentationSpec(
        False, resource_util.FlagNameFormat(self.presentation_name),
        None, {}, None
    ).attribute_to_args_map

  @property
  def _attribute_to_flag_dest_map(self):
    return {
        attr: resource_util.NormalizeFormat(flag)
        for attr, flag in self.attribute_to_flag_map.items()
    }

  @property
  def ignored_flags(self):
    """Returns a map of attribute name to flag name."""
    return _AllRemovedFlags(self._removed_attrs, self.attribute_to_flag_map)

  def _GetParentResource(self, resource_collection):
    parent_collection, _, _ = resource_collection.full_name.rpartition('.')
    return registry.GetAPICollection(
        parent_collection, api_version=self._api_version)

  def IsPrimaryResource(self, resource_collection):
    """Determines whether this resource arg is primary for a given method.

    Primary indicates that this resource arg represents the resource the api
    is fetching, updating, or creating

    Args:
      resource_collection: APICollection | None, collection associated with
        the api method. None if a methodless command.

    Returns:
      bool, true if this resource arg corresponds with the given method
        collection
    """
    if not self.is_primary_resource and self.is_primary_resource is not None:
      return False

    # If validation is disabled, default to resource being primary
    if not resource_collection or self.override_resource_collection:
      return True

    if self.is_parent_resource:
      resource_collection = self._GetParentResource(resource_collection)

    if resource_collection.full_name != self._full_collection_name:
      if self.is_primary_resource:
        raise util.InvalidSchemaError(
            'Collection names do not match for resource argument specification '
            '[{}]. Expected [{}], found [{}]'
            .format(self.name, resource_collection.full_name,
                    self._full_collection_name))
      return False

    if (self._api_version and
        self._api_version != resource_collection.api_version):
      if self.is_primary_resource:
        raise util.InvalidSchemaError(
            'API versions do not match for resource argument specification '
            '[{}]. Expected [{}], found [{}]'
            .format(self.name, resource_collection.api_version,
                    self._api_version))
      return False

    return True

  def _GeneratePresentationSpec(
      self, is_required, presentation_flag_name,
      flag_name_override, ignored_flag_map, group_help=None):
    return presentation_specs.ResourcePresentationSpec(
        presentation_flag_name,
        self._resource_spec,
        group_help=group_help,
        prefixes=False,
        required=is_required,
        flag_name_overrides={**(flag_name_override or {}), **ignored_flag_map},
        plural=self.repeated)

  def GenerateResourceArg(
      self, method, presentation_flag_name=None, flag_name_override=None,
      shared_resource_flags=None, group_help=None):
    """Generates only the resource arg (no update flags)."""

    command_level_fallthroughs = _GenerateFullFallthroughsMap(
        self.command_level_fallthroughs,
        self.attribute_to_flag_map,
        shared_resource_flags, presentation_flag_name)

    ignored_flag_map = _GenerateIgnoredFlagsMap(
        shared_resource_flags,
        self.ignored_flags,
        self.attribute_to_flag_map)

    presentation_spec = self._GeneratePresentationSpec(
        self.IsRequired(method), presentation_flag_name,
        flag_name_override, ignored_flag_map, group_help)

    return concept_parsers.ConceptParser(
        [presentation_spec],
        command_level_fallthroughs=command_level_fallthroughs)

  def ParseResourceArg(self, namespace, group_required=True):
    """Parses the resource ref from namespace (no update flags).

    Args:
      namespace: The argparse namespace.
      group_required: bool, whether parent argument group is required

    Returns:
      The parsed resource ref or None if no resource arg was generated for this
      method.
    """
    # If surrounding argument group is not required, only parse argument
    # if the anchor is specified. Otherwise, user will receive some unncessary
    # errors for missing attribute flags.
    # TODO(b/280668052): This a temporary solution. Whether or not a resource
    # argument should be parsed as required should be fixed in the
    # resource argument and take into account the other arguments specified
    # in the group.
    anchor_specified = _IsAnchorSpecified(
        self._resource_spec,
        namespace,
        self._attribute_to_flag_dest_map,
        self.presentation_name,
        self.clearable)
    if not anchor_specified and not group_required:
      return None

    result = arg_utils.GetFromNamespace(
        namespace.CONCEPTS, self.presentation_name)

    return result and result.Parse()

  def IsApiFieldSpecified(self, namespace):
    if not self.api_fields:
      return False

    return _IsAnchorSpecified(
        self._resource_spec,
        namespace,
        self._attribute_to_flag_dest_map,
        self.presentation_name,
        self.clearable)

  def GetPresentationFlagName(self, resource_collection, is_list_method):
    """Get the anchor argument name for the resource spec.

    Args:
      resource_collection: APICollection | None, collection associated with
        the api method. None if a methodless command.
      is_list_method: bool | None, whether command is associated with list
        method. None if methodless command.

    Returns:
      string, anchor in flag format ie `--foo-bar` or `FOO_BAR`
    """
    # If left unspecified, decide whether the resource is positional based on
    # the method.
    anchor_arg_is_flag = not self.IsPositional(
        resource_collection, is_list_method)
    return (
        '--' + self.presentation_name
        if anchor_arg_is_flag else self.presentation_name)

  def _GenerateUpdateFlags(
      self, resource_collection, is_list_method, shared_resource_flags=None):
    """Creates update flags generator using aptiools message."""
    return update_resource_args.UpdateResourceArgumentGenerator.FromArgData(
        self, resource_collection, is_list_method, shared_resource_flags)

  def _ParseUpdateArgsFromNamespace(
      self, resource_collection, is_list_method, namespace, message):
    """Parses update flags and returns modified apitools message field."""
    return self._GenerateUpdateFlags(
        resource_collection, is_list_method).Parse(namespace, message)

  def Generate(self, methods, shared_resource_flags=None):
    """Generates and returns resource argument.

    Args:
      methods: list[registry.APIMethod], used to generate other arguments.
      shared_resource_flags: [string], list of flags being generated elsewhere.

    Returns:
      Resource argument.
    """
    resource_collection = self._GetMethodCollection(methods)
    is_list_method = _GetIsList(methods)

    if self.clearable:
      return self._GenerateUpdateFlags(
          resource_collection, is_list_method, shared_resource_flags).Generate()
    else:
      return self.GenerateResourceArg(
          resource_collection,
          presentation_flag_name=self.GetPresentationFlagName(
              resource_collection, is_list_method),
          flag_name_override=None,
          shared_resource_flags=shared_resource_flags,
          group_help=self.group_help)

  def Parse(self, method, message, namespace, group_required=True):
    """Sets the argument message value, if any, from the parsed args.

    Args:
      method: registry.APIMethod, used to parse other arguments.
      message: The API message, None for non-resource args.
      namespace: The parsed command line argument namespace.
      group_required: bool, whether parent argument group is required.
        Unused here.
    """
    if self.clearable:
      ref = self._ParseUpdateArgsFromNamespace(
          method and method.resource_argument_collection,
          method.IsList(),
          namespace, message)
    else:
      ref = self.ParseResourceArg(namespace, group_required)

    # Set resource to None only if the user explicitly specified it.
    user_specified = (
        not self.api_fields or self.IsApiFieldSpecified(namespace))
    if not self.parse_resource_into_request or (not ref and not user_specified):
      return

    # For each method path field, get the value from the resource reference.
    arg_utils.ParseResourceIntoMessage(
        ref, method, message,
        message_resource_map=_GetResourceMap(ref, self.resource_method_params),
        request_id_field=self.request_id_field,
        use_relative_name=self.use_relative_name,
        is_primary_resource=self.IsPrimaryResource(
            method and method.resource_argument_collection))


class YAMLMultitypeResourceArgument(YAMLConceptArgument):
  """Encapsulates the spec for the resource arg of a declarative command."""

  def __init__(self, data, group_help, request_api_version=None, **kwargs):
    super(YAMLMultitypeResourceArgument, self).__init__(
        data, group_help, **kwargs)

    self._resources = []
    for resource_data in data.get('resources', []):
      self._resources.append(
          YAMLResourceArgument.FromSpecData(
              resource_data,
              request_api_version,
              is_parent_resource=self.is_parent_resource))

  @property
  def collection(self):
    return None

  @property
  def collections(self):
    return [resource.collection for resource in self._resources]

  @property
  def multitype(self):
    return True

  @property
  def anchors(self):
    return _GetAnchors(self._resource_spec)

  @property
  def attribute_names(self):
    return _GetAttributeNames(self._resource_spec)

  @property
  def presentation_name(self):
    # To get the correct casing (how it should appear on the command line)
    # use GetPresentationFlagName
    if self.flag_name_override:
      return self.flag_name_override
    else:
      return _GetPresentationName(self._resource_spec, self.repeated)

  @property
  def attribute_to_flag_map(self):
    """Returns a map of attribute name to normalized flag name."""
    # Not an accurate attribute to flag name map since it does not include
    # positional vs non-positional or skipped flags. However, it is sufficient
    # for the purposes of determining if a flag is specified.
    return self._GeneratePresentationSpec(
        False, resource_util.FlagNameFormat(self.presentation_name),
        None, {}, None
    ).attribute_to_args_map

  @property
  def _attribute_to_flag_dest_map(self):
    return {
        attr: resource_util.NormalizeFormat(flag)
        for attr, flag in self.attribute_to_flag_map.items()
    }

  @property
  def ignored_flags(self):
    """Returns a map of attribute name to flag name."""
    return _AllRemovedFlags(self._removed_attrs, self.attribute_to_flag_map)

  @property
  def _resource_spec(self):
    """Resource spec generated from the YAML."""

    resource_specs = []
    for sub_resource in self._resources:
      # pylint: disable=protected-access
      if not sub_resource._disable_auto_completers:
        raise ValueError('disable_auto_completers must be True for '
                         'multitype resource argument [{}]'.format(self.name))
      resource_specs.append(sub_resource._resource_spec)
      # pylint: enable=protected-access

    return multitype.MultitypeResourceSpec(self.name, *resource_specs)

  def IsPrimaryResource(self, resource_collection):
    """Determines whether this resource arg is primary for a given method.

    Primary indicates that this resource arg represents the resource the api
    is fetching, updating, or creating

    Args:
      resource_collection: APICollection | None, collection associated with
        the api method. None if a methodless command.

    Returns:
      bool, true if this resource arg corresponds with the given method
        collection
    """
    if not self.is_primary_resource and self.is_primary_resource is not None:
      return False

    for sub_resource in self._resources:
      if sub_resource.IsPrimaryResource(resource_collection):
        return True

    if self.is_primary_resource:
      raise util.InvalidSchemaError(
          'Collection names do not align with resource argument '
          'specification [{}]. Expected [{} version {}], and no contained '
          'resources matched.'.format(
              self.name, resource_collection.full_name,
              resource_collection.api_version))
    return False

  def _GeneratePresentationSpec(
      self, is_required, presentation_flag_name,
      flag_name_override, ignored_flag_map, group_help=None):
    return presentation_specs.MultitypeResourcePresentationSpec(
        presentation_flag_name,
        self._resource_spec,
        group_help=group_help,
        prefixes=False,
        required=is_required,
        flag_name_overrides={**ignored_flag_map, **(flag_name_override or {})},
        plural=self.repeated)

  def GenerateResourceArg(
      self, method, presentation_flag_name=None, flag_name_override=None,
      shared_resource_flags=None, group_help=None):
    """Generates only the resource arg (no update flags)."""

    command_level_fallthroughs = _GenerateFullFallthroughsMap(
        self.command_level_fallthroughs,
        self.attribute_to_flag_map,
        shared_resource_flags, presentation_flag_name)

    ignored_flag_map = _GenerateIgnoredFlagsMap(
        shared_resource_flags,
        self.ignored_flags,
        self.attribute_to_flag_map)

    presentation_spec = self._GeneratePresentationSpec(
        self.IsRequired(method), presentation_flag_name,
        flag_name_override, ignored_flag_map, group_help)

    return concept_parsers.ConceptParser(
        [presentation_spec],
        command_level_fallthroughs=command_level_fallthroughs)

  def ParseResourceArg(self, namespace, group_required=True):
    """Parses the resource ref from namespace (no update flags).

    Args:
      namespace: The argparse namespace.
      group_required: bool, whether parent argument group is required

    Returns:
      The parsed resource ref or None if no resource arg was generated for this
      method.
    """
    # If surrounding argument group is not required, only parse argument
    # if the anchor is specified. Otherwise, user will receive some unncessary
    # errors for missing attribute flags.
    # TODO(b/280668052): This a temporary solution. Whether or not a resource
    # argument should be parsed as required should be fixed in the
    # resource argument and take into account the other arguments specified
    # in the group.
    is_anchor_specified = _IsAnchorSpecified(
        self._resource_spec,
        namespace,
        self._attribute_to_flag_dest_map,
        self.presentation_name,
        self.clearable)
    if not is_anchor_specified and not group_required:
      return None

    result = arg_utils.GetFromNamespace(
        namespace.CONCEPTS, self.presentation_name)

    parsed_result = result and result.Parse()
    return parsed_result and parsed_result.result

  def IsApiFieldSpecified(self, namespace):
    if not self.api_fields:
      return False
    return _IsAnchorSpecified(
        self._resource_spec, namespace,
        self._attribute_to_flag_dest_map, self.presentation_name,
        self.clearable)

  def GetPresentationFlagName(self, resource_collection, is_list_method):
    """Get the anchor argument name for the resource spec.

    Args:
      resource_collection: APICollection | None, collection associated with
        the api method. None if a methodless command.
      is_list_method: bool | None, whether command is associated with list
        method. None if methodless command.

    Returns:
      string, anchor in flag format ie `--foo-bar` or `FOO_BAR`
    """
    # If left unspecified, decide whether the resource is positional based on
    # the method.
    anchor_arg_is_flag = not self.IsPositional(
        resource_collection, is_list_method)
    return (
        '--' + self.presentation_name
        if anchor_arg_is_flag else self.presentation_name)

  def _GenerateUpdateFlags(
      self, resource_collection, is_list_method, shared_resource_flags=None):
    """Creates update flags generator using aptiools message."""
    return update_resource_args.UpdateResourceArgumentGenerator.FromArgData(
        self, resource_collection, is_list_method, shared_resource_flags)

  def _ParseUpdateArgsFromNamespace(
      self, resource_collection, is_list_method, namespace, message):
    """Parses update flags and returns modified apitools message field."""
    return self._GenerateUpdateFlags(
        resource_collection, is_list_method).Parse(namespace, message)

  def Generate(self, methods, shared_resource_flags=None):
    resource_collection = self._GetMethodCollection(methods)
    is_list_method = _GetIsList(methods)

    if self.clearable:
      return self._GenerateUpdateFlags(
          resource_collection, is_list_method, shared_resource_flags).Generate()
    else:
      return self.GenerateResourceArg(
          resource_collection,
          presentation_flag_name=self.GetPresentationFlagName(
              resource_collection, is_list_method),
          flag_name_override=None,
          shared_resource_flags=shared_resource_flags,
          group_help=self.group_help)

  def Parse(self, method, message, namespace, group_required=True):
    if self.clearable:
      ref = self._ParseUpdateArgsFromNamespace(
          method and method.resource_argument_collection,
          method.IsList(),
          namespace, message)
    else:
      ref = self.ParseResourceArg(namespace, group_required)

    # Set resource to None only if the user explicitly specified it.
    user_specified = (
        not self.api_fields or self.IsApiFieldSpecified(namespace))
    if not self.parse_resource_into_request or (not ref and not user_specified):
      return

    # For each method path field, get the value from the resource reference.
    arg_utils.ParseResourceIntoMessage(
        ref, method, message,
        message_resource_map=_GetResourceMap(ref, self.resource_method_params),
        request_id_field=self.request_id_field,
        use_relative_name=self.use_relative_name,
        is_primary_resource=self.IsPrimaryResource(
            method and method.resource_argument_collection))
