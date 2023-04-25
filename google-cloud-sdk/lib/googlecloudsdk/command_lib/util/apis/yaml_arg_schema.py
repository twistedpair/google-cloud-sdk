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

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import multitype
from googlecloudsdk.calliope.concepts import util as resource_util
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.command_lib.util.apis import registry
from googlecloudsdk.command_lib.util.apis import yaml_command_schema_util as util
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs

import six


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


class YAMLArgument(six.with_metaclass(abc.ABCMeta, object)):
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

  @abc.abstractmethod
  def Generate(self, method, message, shared_resource_flags):
    """Generates and returns the base argument."""
    pass

  @abc.abstractmethod
  def Parse(self, method, message, namespace):
    """Parses namespace for argument's value and appends value to req message."""
    pass


class ArgumentGroup(YAMLArgument):
  """Encapsulates data used to generate argument groups.

  Most of the attributes of this object correspond directly to the schema and
  have more complete docs there.

  Attributes:
    help_text: Optional help text for the group.
    required: True to make the group required.
    mutex: True to make the group mutually exclusive.
    hidden: True to make the group hidden.
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
    return cls(
        help_text=data.get('help_text'),
        required=data.get('required', False),
        mutex=data.get('mutex', False),
        hidden=data.get('hidden', False),
        arguments=[YAMLArgument.FromData(item, api_version)
                   for item in data.get('params')],
    )

  def __init__(self, help_text=None, required=False, mutex=False, hidden=False,
               arguments=None):
    self.help_text = help_text
    self.required = required
    self.mutex = mutex
    self.hidden = hidden
    self.arguments = arguments

  def Generate(self, method, message, shared_resource_flags=None):
    """Generates and returns the base argument group.

    Args:
      method: registry.APIMethod, used to generate other arguments
      message: The API message, None for non-resource args.
      shared_resource_flags: [string], list of flags being generated elsewhere

    Returns:
      The base argument group.
    """
    group = base.ArgumentGroup(
        mutex=self.mutex, required=self.required, help=self.help_text,
        hidden=self.hidden)
    for arg in self.arguments:
      group.AddArgument(arg.Generate(method, message, shared_resource_flags))
    return group

  def Parse(self, method, message, namespace):
    """Sets argument group message values, if any, from the parsed args.

    Args:
      method: registry.APIMethod, used to parse sub arguments.
      message: The API message, None for non-resource args.
      namespace: The parsed command line argument namespace.
    """
    for arg in self.arguments:
      arg.Parse(method, message, namespace)


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
        type=util.ParseType(data.get('type')),
        choices=[util.Choice(d) for d in choices] if choices else None,
        default=data.get('default', arg_utils.UNSPECIFIED),
        fallback=util.Hook.FromData(data, 'fallback'),
        processor=util.Hook.FromData(data, 'processor'),
        required=data.get('required', False),
        hidden=data.get('hidden', False),
        action=util.ParseAction(data.get('action'), flag_name),
        repeated=data.get('repeated'),
        disable_unused_arg_check=disable_unused_arg_check,
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
               disable_unused_arg_check=False):
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

  def Generate(self, method, message, shared_resource_flags=None):
    """Generates and returns the base argument.

    Args:
      method: registry.APIMethod, used to generate other arguments.
      message: The API message, None for non-resource args.
      shared_resource_flags: [string], list of flags being generated elsewhere.

    Returns:
      The base argument.
    """
    if message and self.api_field:
      field = arg_utils.GetFieldFromMessage(message, self.api_field)
    else:
      field = None
    return arg_utils.GenerateFlag(field, self)

  def Parse(self, method, message, namespace):
    """Sets the argument message value, if any, from the parsed args.

    Args:
      method: registry.APIMethod, used to parse other arguments.
      message: The API message, None for non-resource args.
      namespace: The parsed command line argument namespace.
    """
    if self.api_field is None:
      return
    value = arg_utils.GetFromNamespace(
        namespace, self.arg_name, fallback=self.fallback)
    if value is None:
      return
    field = arg_utils.GetFieldFromMessage(message, self.api_field)
    value = arg_utils.ConvertValue(
        field, value, repeated=self.repeated, processor=self.processor,
        choices=util.Choice.ToChoiceMap(self.choices))
    arg_utils.SetFieldInMessage(message, self.api_field, value)


class YAMLConceptArgument(six.with_metaclass(abc.ABCMeta, YAMLArgument)):
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
        'required': data.get('required', True),
        'request_api_version': api_version,
    }

    if 'resources' in data['resource_spec']:
      return YAMLMultitypeResourceArgument(resource_spec, help_text, **kwargs)
    return YAMLResourceArgument(resource_spec, help_text, **kwargs)

  def __init__(self, data, group_help, is_positional=None, removed_flags=None,
               is_parent_resource=False, is_primary_resource=None,
               arg_name=None, command_level_fallthroughs=None,
               display_name_hook=None, request_id_field=None,
               resource_method_params=None, parse_resource_into_request=True,
               use_relative_name=True, override_resource_collection=False,
               required=True, **unused_kwargs):
    self.flag_name_override = arg_name
    self.group_help = group_help
    self.is_positional = is_positional
    self.is_parent_resource = is_parent_resource
    self.is_primary_resource = is_primary_resource
    self.removed_flags = removed_flags or []
    self.command_level_fallthroughs = self._GenerateFallthroughsMap(
        command_level_fallthroughs)
    # TODO(b/274890004): Remove data.get('request_id_field')
    self.request_id_field = request_id_field or data.get('request_id_field')
    self.resource_method_params = resource_method_params or {}
    self.parse_resource_into_request = parse_resource_into_request
    self.use_relative_name = use_relative_name
    self.override_resource_collection = override_resource_collection
    self.required = required

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

  @abc.abstractmethod
  def IsPrimaryResource(self, resource_collection):
    """Determines if this resource arg is the primary resource."""
    pass

  @abc.abstractmethod
  def ParseResourceArg(self, method, namespace):
    """Parses the resource ref from namespace."""
    pass

  def _ParseResourceArg(self, method, namespace):
    """Gets the resource ref for the resource specified as the positional arg.

    Args:
      method: registry.APIMethod, method we are parsing the resource for.
      namespace: The argparse namespace.

    Returns:
      The parsed resource ref or None if no resource arg was generated for this
      method.
    """
    result = arg_utils.GetFromNamespace(
        namespace.CONCEPTS, self._GetAnchorArgName(method))

    if result:
      result = result.Parse()

    if isinstance(result, multitype.TypedConceptResult):
      result = result.result
    return result

  def _GetAnchorArgName(self, method=None):
    """Get the anchor argument name for the resource spec."""
    resource_spec = self._GenerateResourceSpec(
        method and method.resource_argument_collection)

    if self.flag_name_override:
      flag_name = self.flag_name_override
    elif hasattr(resource_spec, 'anchor'):
      flag_name = resource_spec.anchor.name
    else:
      flag_name = self.name or resource_spec.name

    # If left unspecified, decide whether the resource is positional based on
    # the method.
    if self.is_positional is None:
      anchor_arg_is_flag = False
      if method:
        anchor_arg_is_flag = method.IsList()
    else:
      anchor_arg_is_flag = not self.is_positional
    anchor_arg_name = (
        '--' + flag_name if anchor_arg_is_flag
        else flag_name)
    return anchor_arg_name

  def _GetResourceMap(self, ref):
    message_resource_map = {}
    for message_field_name, param_str in self.resource_method_params.items():
      value = util.FormatResourceAttrStr(param_str, ref)
      message_resource_map[message_field_name] = value
    return message_resource_map

  def _GenerateFallthroughsMap(self, command_level_fallthroughs_data):
    """Generate a map of command-level fallthroughs."""
    command_level_fallthroughs_data = command_level_fallthroughs_data or {}
    command_level_fallthroughs = {}

    def _FallthroughStringFromData(fallthrough_data):
      if fallthrough_data.get('is_positional', False):
        return resource_util.PositionalFormat(fallthrough_data['arg_name'])
      return resource_util.FlagNameFormat(fallthrough_data['arg_name'])

    for attribute_name, fallthroughs_data in six.iteritems(
        command_level_fallthroughs_data):
      fallthroughs_list = [_FallthroughStringFromData(fallthrough)
                           for fallthrough in fallthroughs_data]
      command_level_fallthroughs[attribute_name] = fallthroughs_list

    return command_level_fallthroughs

  def _GenerateConceptParser(self, method, resource_spec, attribute_names,
                             shared_resource_flags=None):
    """Generates a ConceptParser from YAMLConceptArgument.

    Args:
      method: registry.APIMethod, helps determine the arg name
      resource_spec: concepts.ResourceSpec, used to create PresentationSpec
      attribute_names: names of resource attributes
      shared_resource_flags: [string], list of flags being generated elsewhere

    Returns:
      ConceptParser that will be added to the parser.
    """
    shared_resource_flags = shared_resource_flags or []
    ignored_fields = (list(concepts.IGNORED_FIELDS.values()) +
                      self.removed_flags + shared_resource_flags)
    no_gen = {
        n: ''
        for n in ignored_fields if n in attribute_names
    }

    anchor_arg_name = self._GetAnchorArgName(method)

    command_level_fallthroughs = {}
    arg_fallthroughs = self.command_level_fallthroughs.copy()
    arg_fallthroughs.update(
        {n: ['--' + n] for n in shared_resource_flags if n in attribute_names})

    concept_parsers.UpdateFallthroughsMap(
        command_level_fallthroughs,
        anchor_arg_name,
        arg_fallthroughs)
    presentation_spec_class = presentation_specs.ResourcePresentationSpec

    if isinstance(resource_spec, multitype.MultitypeResourceSpec):
      presentation_spec_class = (
          presentation_specs.MultitypeResourcePresentationSpec)

    return concept_parsers.ConceptParser(
        [presentation_spec_class(
            anchor_arg_name,
            resource_spec,
            self.group_help,
            prefixes=False,
            required=self.required,
            flag_name_overrides=no_gen)],
        command_level_fallthroughs=command_level_fallthroughs)


class YAMLResourceArgument(YAMLConceptArgument):
  """Encapsulates the spec for the resource arg of a declarative command."""

  @classmethod
  def FromSpecData(cls, data):
    """Create a resource argument with no command-level information configured.

    Given just the reusable resource specification (such as attribute names
    and fallthroughs, it can be used to generate a ResourceSpec. Not suitable
    for adding directly to a command as a solo argument.

    Args:
      data: the yaml resource definition.

    Returns:
      YAMLResourceArgument with no group help or flag name information.
    """
    if not data:
      return None

    return cls(data, None)

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
    self._attribute_data = data['attributes']
    self._disable_auto_completers = data.get('disable_auto_completers', True)

    for removed in self.removed_flags:
      if removed not in self.attribute_names:
        raise util.InvalidSchemaError(
            'Removed flag [{}] for resource arg [{}] references an attribute '
            'that does not exist. Valid attributes are [{}]'.format(
                removed, self.name, ', '.join(self.attribute_names)))

  @property
  def attribute_names(self):
    return [a['attribute_name'] for a in self._attribute_data]

  @property
  def collection(self):
    return registry.GetAPICollection(
        self._full_collection_name, api_version=self._api_version)

  def IsPrimaryResource(self, resource_collection=None):
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

  def Generate(self, method, message, shared_resource_flags=None):
    resource_spec = self._GenerateResourceSpec(
        method and method.resource_argument_collection)

    return self._GenerateConceptParser(
        method, resource_spec, self.attribute_names, shared_resource_flags)

  def Parse(self, method, message, namespace):
    ref = self.ParseResourceArg(method, namespace)
    if not self.parse_resource_into_request or not ref:
      return message

    # For each method path field, get the value from the resource reference.
    arg_utils.ParseResourceIntoMessage(
        ref, method, message,
        message_resource_map=self._GetResourceMap(ref),
        request_id_field=self.request_id_field,
        use_relative_name=self.use_relative_name,
        is_primary_resource=self.IsPrimaryResource(
            method and method.resource_argument_collection))

  def ParseResourceArg(self, method, namespace):
    return self._ParseResourceArg(method, namespace)

  def _GetParentResource(self, resource_collection):
    parent_collection, _, _ = resource_collection.full_name.rpartition('.')
    return registry.GetAPICollection(
        parent_collection, api_version=self._api_version)

  def _GenerateResourceSpec(self, resource_collection=None):
    """Validates if the resource matches what the method specifies.

    Args:
      resource_collection: registry.APICollection, The collection that the
        resource arg must be for. This does some extra validation to
        ensure that resource arg is for the correct collection and api_version.
        If not specified, the resource arg will just be loaded based on the
        collection it specifies.

    Returns:
      concepts.ResourceSpec, The generated specification that can be added to
      a parser.
    """

    if (not resource_collection
        or self.override_resource_collection
        or not self.IsPrimaryResource(resource_collection)):
      resource_collection = self.collection
    elif resource_collection and self.is_parent_resource:
      resource_collection = self._GetParentResource(resource_collection)

    # If attributes do not match resource_collection.detailed_params, will
    # raise InvalidSchema error
    attributes = concepts.ParseAttributesFromData(
        self._attribute_data, resource_collection.detailed_params)

    return concepts.ResourceSpec(
        resource_collection.full_name,
        resource_name=self.name,
        api_version=resource_collection.api_version,
        disable_auto_completers=self._disable_auto_completers,
        plural_name=self._plural_name,
        is_positional=self.is_positional,
        **{attribute.parameter_name: attribute for attribute in attributes})


class YAMLMultitypeResourceArgument(YAMLConceptArgument):
  """Encapsulates the spec for the resource arg of a declarative command."""

  def __init__(self, data, group_help, **kwargs):
    super(YAMLMultitypeResourceArgument, self).__init__(
        data, group_help, **kwargs)

    self._resources = data.get('resources') or []

  @property
  def collection(self):
    return None

  @property
  def attribute_names(self):
    attribute_names = []
    for sub_resource in self._resources:
      sub_resource_arg = YAMLResourceArgument.FromSpecData(sub_resource)
      for attribute_name in sub_resource_arg.attribute_names:
        if attribute_name not in attribute_names:
          attribute_names.append(attribute_name)
    return attribute_names

  def IsPrimaryResource(self, resource_collection):
    if not self.is_primary_resource and self.is_primary_resource is not None:
      return False

    for sub_resource in self._resources:
      sub_resource_arg = YAMLResourceArgument.FromSpecData(sub_resource)
      if sub_resource_arg.IsPrimaryResource(resource_collection):
        return True

    if self.is_primary_resource:
      raise util.InvalidSchemaError(
          'Collection names do not align with resource argument '
          'specification [{}]. Expected [{} version {}], and no contained '
          'resources matched.'.format(
              self.name, resource_collection.full_name,
              resource_collection.api_version))
    return True

  def Generate(self, method, message, shared_resource_flags=None):
    resource_spec = self._GenerateResourceSpec(
        method and method.resource_argument_collection)

    return self._GenerateConceptParser(
        method, resource_spec, self.attribute_names, shared_resource_flags)

  def Parse(self, method, message, namespace):
    ref = self.ParseResourceArg(method, namespace)
    if not self.parse_resource_into_request or not ref:
      return message

    # For each method path field, get the value from the resource reference.
    arg_utils.ParseResourceIntoMessage(
        ref, method, message,
        message_resource_map=self._GetResourceMap(ref),
        request_id_field=self.request_id_field,
        use_relative_name=self.use_relative_name,
        is_primary_resource=self.IsPrimaryResource(
            method and method.resource_argument_collection))

  def ParseResourceArg(self, method, namespace):
    return self._ParseResourceArg(method, namespace)

  def _GenerateResourceSpec(self, resource_collection=None):
    """Validates if the resource matches what the method specifies.

    Args:
      resource_collection: registry.APICollection, The collection that the
        resource arg must be for. This does some extra validation to
        ensure that resource arg is for the correct collection and api_version.
        If not specified, the resource arg will just be loaded based on the
        collection it specifies.

    Returns:
      multitype.MultitypeResourceSpec, The generated specification that can be
      added to a parser.
    """

    resource_specs = []
    # Need to find a matching collection for validation, if the collection
    # is specified.
    for sub_resource in self._resources:
      # pylint: disable=protected-access
      sub_resource_arg = YAMLResourceArgument.FromSpecData(sub_resource)
      if not sub_resource_arg._disable_auto_completers:
        raise ValueError('disable_auto_completers must be True for '
                         'multitype resource argument [{}]'.format(self.name))
      sub_resource_spec = sub_resource_arg._GenerateResourceSpec(
          resource_collection)
      resource_specs.append(sub_resource_spec)
      # pylint: enable=protected-access

    return multitype.MultitypeResourceSpec(self.name, *resource_specs)
