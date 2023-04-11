# -*- coding: utf-8 -*- #
# Copyright 2017 Google LLC. All Rights Reserved.
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

"""Classes that generate and parse arguments for apitools messages."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.protorpclite import messages
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.command_lib.util.apis import update
from googlecloudsdk.command_lib.util.apis import yaml_arg_schema
from googlecloudsdk.command_lib.util.apis import yaml_command_schema
from googlecloudsdk.command_lib.util.apis import yaml_command_schema_util as util
from googlecloudsdk.command_lib.util.args import labels_util
from googlecloudsdk.core import resources
from googlecloudsdk.core.resource import resource_property


class Error(Exception):
  """Base class for this module's exceptions."""
  pass


def _GetLabelsClass(message, api_field):
  return arg_utils.GetFieldFromMessage(message, api_field).type


def _ParseLabelsIntoCreateMessage(message, args, api_field):
  labels_cls = _GetLabelsClass(message, api_field)
  labels_field = labels_util.ParseCreateArgs(args, labels_cls)
  arg_utils.SetFieldInMessage(message, api_field, labels_field)


def _AddLabelsToUpdateMask(static_field, update_mask_path):
  if (update_mask_path not in static_field) or (
      not static_field[update_mask_path]):
    static_field[update_mask_path] = 'labels'
    return

  if 'labels' in static_field[update_mask_path].split(','):
    return

  static_field[
      update_mask_path] = static_field[update_mask_path] + ',' + 'labels'


def _RetrieveFieldValueFromMessage(message, api_field):
  path = api_field.split('.')
  for field_name in path:
    try:
      message = getattr(message, field_name)
    except AttributeError:
      raise AttributeError(
          'The message does not have field specified in {}.'.format(api_field))
  return message


def _ParseLabelsIntoUpdateMessage(message, args, api_field):
  """Find diff between existing labels and args, set labels into the message."""
  diff = labels_util.Diff.FromUpdateArgs(args)
  # Do nothing if 'labels' arguments weren't specified.
  if not diff.MayHaveUpdates():
    return False
  existing_labels = _RetrieveFieldValueFromMessage(message, api_field)
  label_cls = _GetLabelsClass(message, api_field)
  update_result = diff.Apply(label_cls, existing_labels)
  if update_result.needs_update:
    arg_utils.SetFieldInMessage(message, api_field, update_result.labels)
  return True


def _GetResources(params):
  """Retrieves all resource args from the arg_info tree.

  Args:
    params: an ArgGroup or list of args to parse through.

  Returns:
    YAMLConceptArgument (resource arg) list.
  """
  if isinstance(params, yaml_arg_schema.YAMLConceptArgument):
    return [params]
  if isinstance(params, yaml_arg_schema.Argument):
    return []
  if isinstance(params, yaml_arg_schema.ArgumentGroup):
    params = params.arguments

  result = []
  for param in params:
    result.extend(_GetResources(param))

  return result


def _GetPrimaryResource(resource_params, resource_collection):
  """Retrieves the primary resource arg.

  Args:
    resource_params: list of YAMLConceptParser
    resource_collection: registry.APICollection, resource collection
      associated with method

  Returns:
    YAMLConceptArgument (resource arg) or None.
  """

  # No resource params occurs if resource args are added through a hook.
  if not resource_params:
    return None

  primary_resources = [
      arg for arg in resource_params
      if arg.IsPrimaryResource(resource_collection)]

  if not primary_resources:
    if resource_collection:
      full_name = resource_collection.full_name
      api_version = resource_collection.api_version
    else:
      full_name = None
      api_version = None

    raise util.InvalidSchemaError(
        'No resource args were found that correspond with [{name} {version}]. '
        'Add resource arguments that corresponds with request.method '
        'collection [{name} {version}]. HINT: Can set resource arg '
        'is_primary_resource to True in yaml schema to receive more assistance '
        'with validation.'.format(
            name=full_name, version=api_version))

  if len(primary_resources) > 1:
    primary_resource_names = [arg.name for arg in primary_resources]
    raise util.InvalidSchemaError(
        'Only one resource arg can be listed as primary. Remove one of the '
        'primary resource args [{}] or set is_primary_resource to False in '
        'yaml schema.'.format(', '.join(primary_resource_names)))

  return primary_resources[0]


def _GetSharedAttributes(resource_params):
  """Retrieves shared attributes between resource args.

  Args:
    resource_params: [yaml_arg_schema.Argument], yaml argument tree

  Returns:
    Map of attribute names to list of resources that contain that attribute.
  """
  resource_names = set()
  attributes = {}
  for arg in resource_params:
    if arg.name in resource_names:
      raise util.InvalidSchemaError(
          'More than one resource argument has the name [{}]. Remove one '
          'of the duplicate resource declarations.'.format(arg.name))
    else:
      resource_names.add(arg.name)

    for attribute_name in arg.attribute_names:
      if (attribute_name not in arg.removed_flags and
          not concepts.IGNORED_FIELDS.get(attribute_name)):
        attributes[attribute_name] = attributes.get(attribute_name, set())

        if arg.name in attributes[attribute_name]:
          raise util.InvalidSchemaError(
              'Attribute {} listed more than once in resource {}. '
              'Remove one of the duplicate attribute declarations.'.format(
                  attribute_name, arg.name))

        attributes[attribute_name].add(arg.name)

  return attributes


class DeclarativeArgumentGenerator(object):
  """An argument generator that operates off a declarative configuration.

  When using this generator, you must provide attributes for the arguments that
  should be generated. All resource arguments must be provided and arguments
  will only be generated for API fields for which attributes were provided.
  """

  def __init__(self, method, arg_info):
    """Creates a new Argument Generator.

    Args:
      method: APIMethod, The method to generate arguments for.
      arg_info: [yaml_arg_schema.Argument], Information about
        request fields and how to map them into arguments.
    """
    self.method = method
    self.arg_info = arg_info

    self.resource_args = _GetResources(self.arg_info)
    self.primary_resource_arg = _GetPrimaryResource(
        self.resource_args,
        self.method and self.method.resource_argument_collection)

  def GenerateArgs(self):
    """Generates all the CLI arguments required to call this method.

    Returns:
      {str, calliope.base.Action}, A map of field name to the argument.
    """
    # message used to get field types while generating flags
    message = None
    if self.method:
      message = self.method.GetRequestType()

    flag_map = _GetSharedAttributes(self.resource_args)
    shared_resource_flags = []
    for attribute, resource_args in flag_map.items():
      if len(resource_args) > 1:
        shared_resource_flags.append(attribute)

    args = [arg.Generate(self.method, message, shared_resource_flags)
            for arg in self.arg_info]

    primary = self.primary_resource_arg and self.primary_resource_arg.name

    for arg in shared_resource_flags:
      resource_names = list(flag_map.get(arg))
      resource_names.sort(
          key=lambda name: '' if primary and name == primary else name)

      args.append(base.Argument(
          '--' + arg,
          help='For resources [{}], provides fallback value for resource '
               '{attr} attribute. When the resource\'s full URI path is not '
               'provided, {attr} will fallback to this flag value.'.format(
                   ', '.join(resource_names), attr=arg)))

    return args

  def CreateRequest(self,
                    namespace,
                    static_fields=None,
                    labels=None,
                    command_type=None,
                    override_method=None,
                    existing_message=None):
    """Generates the request object for the method call from the parsed args.

    Args:
      namespace: The argparse namespace.
      static_fields: {str, value}, A mapping of API field name to value to
        insert into the message. This is a convenient way to insert extra data
        while the request is being constructed for fields that don't have
        corresponding arguments.
      labels: The labels section of the command spec.
      command_type: Type of the command, i.e. CREATE, UPDATE.
      override_method: APIMethod, The method other than self.method, this is
        used when the command has more than one API call.
      existing_message: the apitools message returned from server, which is used
        to construct the to-be-modified message when the command follows
        get-modify-update pattern.

    Returns:
      The apitools message to be send to the method.
    """
    message_type = (override_method or self.method).GetRequestType()
    message = message_type()

    # If an apitools message is provided, use the existing one by default
    # instead of creating an empty one.
    if existing_message:
      message = arg_utils.ParseExistingMessageIntoMessage(
          message, existing_message, self.method)

    # Add labels into message
    if labels:
      if command_type == yaml_command_schema.CommandType.CREATE:
        _ParseLabelsIntoCreateMessage(message, namespace, labels.api_field)
      elif command_type == yaml_command_schema.CommandType.UPDATE:
        need_update = _ParseLabelsIntoUpdateMessage(message, namespace,
                                                    labels.api_field)
        if need_update:
          update_mask_path = update.GetMaskFieldPath(override_method)
          _AddLabelsToUpdateMask(static_fields, update_mask_path)

    # Insert static fields into message.
    arg_utils.ParseStaticFieldsIntoMessage(message, static_fields=static_fields)

    # Parse api Fields into message.
    for arg in self.arg_info:
      arg.Parse(self.method, message, namespace)

    return message

  def GetRequestResourceRef(self, namespace):
    """Gets a resource reference for the resource being operated on.

    Args:
      namespace: The argparse namespace.

    Returns:
      resources.Resource, The parsed resource reference.
    """
    if not self.primary_resource_arg:
      return None
    return self.primary_resource_arg.ParseResourceArg(self.method, namespace)

  def GetResponseResourceRef(self, id_value, namespace):
    """Gets a resource reference for a resource returned by a list call.

    It parses the namespace to find a reference to the parent collection and
    then creates a reference to the child resource with the given id_value.

    Args:
      id_value: str, The id of the child resource that was returned.
      namespace: The argparse namespace.

    Returns:
      resources.Resource, The parsed resource reference.
    """
    parent_ref = self.GetRequestResourceRef(namespace)
    return resources.REGISTRY.Parse(
        id_value,
        collection=self.method.collection.full_name,
        api_version=self.method.collection.api_version,
        params=parent_ref.AsDict())

  def Limit(self, namespace):
    """Gets the value of the limit flag (if present)."""
    return arg_utils.Limit(self.method, namespace)

  def PageSize(self, namespace):
    """Gets the value of the page size flag (if present)."""
    return arg_utils.PageSize(self.method, namespace)


class AutoArgumentGenerator(object):
  """An argument generator to generate arguments for all fields in a message.

  When using this generator, you don't provide any manual configuration for
  arguments, it is all done automatically based on the request messages.

  There are two modes for this generator. In 'raw' mode, no modifications are
  done at all to the generated fields. In normal mode, certain list fields are
  not generated and instead our global list flags are used (and orchestrate
  the proper API fields automatically). In both cases, we generate additional
  resource arguments for path parameters.
  """
  FLAT_RESOURCE_ARG_NAME = 'resource'
  IGNORABLE_LIST_FIELDS = {'filter', 'pageToken', 'orderBy'}

  def __init__(self, method, raw=False):
    """Creates a new Argument Generator.

    Args:
      method: APIMethod, The method to generate arguments for.
      raw: bool, True to do no special processing of arguments for list
        commands. If False, typical List command flags will be added in and the
        equivalent API fields will be ignored.
    """
    self.method = method
    self.raw = raw
    self.is_atomic = self.method.detailed_params != self.method.params

    self.ignored_fields = set()
    if not raw and self.method.IsPageableList():
      self.ignored_fields |= AutoArgumentGenerator.IGNORABLE_LIST_FIELDS
      batch_page_size_field = self.method.BatchPageSizeField()
      if batch_page_size_field:
        self.ignored_fields.add(batch_page_size_field)

  def GenerateArgs(self):
    """Generates all the CLI arguments required to call this method.

    Returns:
      {str, calliope.base.Action}, A map of field name to the argument.
    """
    seen = set()
    args = []

    def _UpdateArgs(arguments):
      """Update args."""
      for arg in arguments:
        try:
          name = arg.name
        except IndexError:
          # An argument group does not have a name.
          pass
        else:
          if name in seen:
            continue
          seen.add(name)
        args.append(arg)

    # NOTICE: The call order is significant. Duplicate arg names are possible.
    # The first of the duplicate args entered wins.
    _UpdateArgs(self._GenerateResourceArg())
    _UpdateArgs(self._GenerateArguments('', self.method.GetRequestType()))
    _UpdateArgs(self._GenerateListMethodFlags())

    return args

  def CreateRequest(self, namespace):
    """Generates the request object for the method call from the parsed args.

    Args:
      namespace: The argparse namespace.

    Returns:
      The apitools message to be send to the method.
    """
    request_type = self.method.GetRequestType()
    # Recursively create the message and sub-messages.
    fields = self._ParseArguments(namespace, '', request_type)

    # For each actual method path field, add the attribute to the request.
    ref = self._ParseResourceArg(namespace)
    if ref:
      relative_name = ref.RelativeName()
      fields.update({f: getattr(ref, f, relative_name)
                     for f in self.method.params})
    return request_type(**fields)

  def Limit(self, namespace):
    """Gets the value of the limit flag (if present)."""
    if not self.raw:
      return arg_utils.Limit(self.method, namespace)

  def PageSize(self, namespace):
    """Gets the value of the page size flag (if present)."""
    if not self.raw:
      return arg_utils.PageSize(self.method, namespace)

  def _GenerateListMethodFlags(self):
    """Generates all the CLI flags for a List command.

    Returns:
      {str, calliope.base.Action}, A map of field name to the argument.
    """
    flags = []
    if not self.raw and self.method.IsList():
      flags.append(base.FILTER_FLAG)
      flags.append(base.SORT_BY_FLAG)
      if self.method.IsPageableList() and self.method.ListItemField():
        # We can use YieldFromList() with a limit.
        flags.append(base.LIMIT_FLAG)
        if self.method.BatchPageSizeField():
          # API supports page size.
          flags.append(base.PAGE_SIZE_FLAG)
    return flags

  def _GenerateArguments(self, prefix, message):
    """Gets the arguments to add to the parser that appear in the method body.

    Args:
      prefix: str, A string to prepend to the name of the flag. This is used
        for flags representing fields of a submessage.
      message: The apitools message to generate the flags for.

    Returns:
      {str, calliope.base.Argument}, A map of field name to argument.
    """
    args = []
    field_helps = arg_utils.FieldHelpDocs(message)
    for field in message.all_fields():
      field_help = field_helps.get(field.name, None)
      name = self._GetArgName(field.name, field_help)
      if not name:
        continue
      name = prefix + name
      if field.variant == messages.Variant.MESSAGE:
        sub_args = self._GenerateArguments(name + '.', field.type)
        if sub_args:
          help_text = (name + ': ' + field_help) if field_help else ''
          group = base.ArgumentGroup(help=help_text)
          args.append(group)
          for arg in sub_args:
            group.AddArgument(arg)
      else:
        attributes = yaml_arg_schema.Argument(name, name, field_help)
        arg = arg_utils.GenerateFlag(field, attributes, fix_bools=False,
                                     category='MESSAGE')
        if not arg.kwargs.get('help'):
          arg.kwargs['help'] = 'API doc needs help for field [{}].'.format(name)
        args.append(arg)
    return args

  def _GenerateResourceArg(self):
    """Gets the flags to add to the parser that appear in the method path.

    Returns:
      {str, calliope.base.Argument}, A map of field name to argument.
    """
    args = []
    field_names = (self.method.request_collection.detailed_params
                   if self.method.request_collection else None)
    if not field_names:
      return args
    field_helps = arg_utils.FieldHelpDocs(self.method.GetRequestType())
    default_help = 'For substitution into: ' + self.method.detailed_path

    # Make a dedicated positional in addition to the flags for each part of
    # the URI path.
    arg = base.Argument(
        AutoArgumentGenerator.FLAT_RESOURCE_ARG_NAME,
        nargs='?',
        help='The GRI for the resource being operated on.')
    args.append(arg)

    for field in field_names:
      arg = base.Argument(
          '--' + field,
          metavar=resource_property.ConvertToAngrySnakeCase(field),
          category='RESOURCE',
          help=field_helps.get(field, default_help))
      args.append(arg)
    return args

  def _ParseArguments(self, namespace, prefix, message):
    """Recursively generates data for the request message and any sub-messages.

    Args:
      namespace: The argparse namespace containing the all the parsed arguments.
      prefix: str, The flag prefix for the sub-message being generated.
      message: The apitools class for the message.

    Returns:
      A dict of message field data that can be passed to an apitools Message.
    """
    kwargs = {}
    for field in message.all_fields():
      arg_name = self._GetArgName(field.name)
      if not arg_name:
        continue
      arg_name = prefix + arg_name
      # Field is a sub-message, recursively generate it.
      if field.variant == messages.Variant.MESSAGE:
        sub_kwargs = self._ParseArguments(namespace, arg_name + '.', field.type)
        if sub_kwargs:
          # Only construct the sub-message if we have something to put in it.
          value = field.type(**sub_kwargs)
          kwargs[field.name] = value if not field.repeated else [value]
      # Field is a scalar, just get the value.
      else:
        value = arg_utils.GetFromNamespace(namespace, arg_name)
        if value is not None:
          kwargs[field.name] = arg_utils.ConvertValue(field, value)
    return kwargs

  def _ParseResourceArg(self, namespace):
    """Gets the resource ref for the resource specified as the positional arg.

    Args:
      namespace: The argparse namespace.

    Returns:
      The parsed resource ref or None if no resource arg was generated for this
      method.
    """
    field_names = (self.method.request_collection.detailed_params
                   if self.method.request_collection else None)
    if not field_names:
      return
    r = getattr(namespace, AutoArgumentGenerator.FLAT_RESOURCE_ARG_NAME)
    enforce_collection = getattr(namespace, 'enforce_collection', True)

    params = {}
    defaults = {}
    for f in field_names:
      value = getattr(namespace, f)
      if value:
        params[f] = value
      else:
        default = arg_utils.DEFAULT_PARAMS.get(f, lambda: None)()
        if default:
          defaults[f] = default

    if not r and not params and len(defaults) < len(field_names):
      # No values were explicitly given and there are not enough defaults for
      # the parse to work.
      return None

    defaults.update(params)
    return resources.REGISTRY.Parse(
        r, collection=self.method.request_collection.full_name,
        enforce_collection=enforce_collection,
        api_version=self.method.request_collection.api_version,
        params=defaults)

  def _GetArgName(self, field_name, field_help=None):
    """Gets the name of the argument to generate for the field.

    Args:
      field_name: str, The name of the field.
      field_help: str, The help for the field in the API docs.

    Returns:
      str, The name of the argument to generate, or None if this field is output
      only or should be ignored.
    """
    if field_help and arg_utils.IsOutputField(field_help):
      return None
    if field_name in self.ignored_fields:
      return None
    if (field_name == self.method.request_field and
        field_name.lower().endswith('request')):
      return 'request'
    return field_name
