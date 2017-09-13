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

"""Utilities related to adding flags for the gcloud meta api commands."""

import re

from apitools.base.protorpclite import messages

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.util.apis import yaml_command_schema
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.resource import resource_property


def _EnumNameToChoice(name):
  return name.replace('_', '-').lower()


_TYPES = {
    messages.Variant.DOUBLE: float,
    messages.Variant.FLOAT: float,

    messages.Variant.INT64: long,
    messages.Variant.UINT64: long,
    messages.Variant.SINT64: long,

    messages.Variant.INT32: int,
    messages.Variant.UINT32: int,
    messages.Variant.SINT32: int,

    messages.Variant.STRING: str,

    # TODO(b/38000796): Do something with bytes.
    messages.Variant.BYTES: None,
    # For boolean flags, we wan't to create a flag with action 'store_true'
    # rather than a flag that takes a value and converts it to a boolean.
    messages.Variant.BOOL: None,
    # For enums, we want to accept upper and lower case from the user, but
    # always compare against lowercase enum chioces.
    messages.Variant.ENUM: _EnumNameToChoice,
    messages.Variant.MESSAGE: None,
}


# TODO(b/38000796): Use the same defaults as the normal resource parser.
DEFAULT_PARAMS = {
    'project': properties.VALUES.core.project.Get,
    'projectId': properties.VALUES.core.project.Get,
    'projectsId': properties.VALUES.core.project.Get,
}


class Error(Exception):
  """Base class for this module's exceptions."""
  pass


class MissingArgInformation(Error):
  """Exception for when there is no arg information for an API field."""

  def __init__(self, field):
    super(MissingArgInformation, self).__init__(
        'You must provide argument information for API field: [{}]'
        .format(field))


class ArgumentGenerator(object):
  """Class to generate and parse argparse flags from apitools message fields."""
  FLAT_RESOURCE_ARG_NAME = 'resource'
  AUTO_RENAME_FIELDS = {'projectId': 'project',
                        'projectsId': 'project'}
  IGNORABLE_LIST_FIELDS = {'filter', 'pageToken', 'orderBy'}

  def __init__(self, method, arg_info=None, raw=False, clean_surface=False,
               builtin_args=None):
    """Creates a new Argument Generator.

    Args:
      method: APIMethod, The method to generate arguments for.
      arg_info: {str: yaml_command_schema.Argument}, Optional information about
        request parameters and how to map them into arguments.
      raw: bool, True to do no special processing of arguments for list
        commands. If False, typical List command flags will be added in and the
        equivalent API fields will be ignored.
      clean_surface: bool, If true, we try to clean up the surface by making
        a few common transformations. This includes things like auto-renaming
        common fields (like projectsId) and naming the resource argument after
        the actual request field it represents instead of adding an additional
        'resource' argument. It also does not generate flags for atomic name
        fields for resources using that model. This only works if raw = False.
      builtin_args: {str}, A set of argument names that are already registered
        as builtin flags (like --project) and should not be generated. When
        parsing, the value of the builtin flag will be used.
    """
    self.method = method
    self.arg_info = arg_info
    self.builtin_args = builtin_args or set()
    self.raw = raw
    self.clean_surface = not raw and clean_surface
    self.is_atomic = self.method.detailed_params != self.method.params

    self.auto_rename_fields = dict()
    self.ignored_fields = set()
    if not raw:
      if self.clean_surface:
        self.auto_rename_fields.update(ArgumentGenerator.AUTO_RENAME_FIELDS)
      if self.method.IsPageableList():
        self.ignored_fields |= ArgumentGenerator.IGNORABLE_LIST_FIELDS
        batch_page_size_field = self.method.BatchPageSizeField()
        if batch_page_size_field:
          self.ignored_fields.add(batch_page_size_field)

  def GenerateArgs(self, include_global_list_flags=True):
    """Generates all the CLI arguments required to call this method.

    Args:
      include_global_list_flags: bool, True to generate flags for things like
        filter, sort-by, etc. This should be turned off if you are generating
        arguments into a command that is already a base.ListCommand and so will
        already have these common flags.

    Returns:
      {str, calliope.base.Action}, A map of field name to the argument.
    """
    args = {}
    if include_global_list_flags:
      args.update(self._GenerateListMethodFlags())
    args.update(self._GenerateMessageFieldsFlags(
        '', self.method.GetRequestType()))
    args.update(self._GenerateResourceArg())
    return {k: v for k, v in args.iteritems() if k not in self.builtin_args}

  @property
  def resource_arg_name(self):
    """Gets the type of the resource being operated on.

    This is based off the name of the final positional parameter in the API
    request.


    Returns:
      The type of resource being operated on (i.e. instance, registry, disk,
      etc).
    """
    field_names = self.method.ResourceFieldNames()
    if not field_names:
      return None
    return self._GetArgAttributes(field_names[-1], required=True).arg_name

  def CreateRequest(self, namespace, static_fields=None,
                    resource_method_params=None):
    """Generates the request object for the method call from the parsed args.

    Args:
      namespace: The argparse namespace.
      static_fields: {str, value}, A mapping of API field name to value to
        insert into the message. This is a convenient way to insert extra data
        while the request is being constructed for fields that don't have
        corresponding arguments.
      resource_method_params: {str: str}, A mapping of API method parameter name
        to resource ref attribute name when the API method uses non-standard
        names.

    Returns:
      The apitools message to be send to the method.
    """
    if resource_method_params is None:
      resource_method_params = {}

    request_type = self.method.GetRequestType()
    # Recursively create the message and sub-messages.

    fields = self._ParseMessageFieldsFlags(
        namespace, '', request_type, (static_fields or {}), is_root=True)

    # For each actual method path field, add the attribute to the request.
    ref = self._ParseResourceArg(namespace)
    if ref:
      relative_name = ref.RelativeName()
      fields.update(
          {f: getattr(ref, resource_method_params.get(f, f), relative_name)
           for f in self.method.params})
    return request_type(**fields)

  def GetRequestResourceRef(self, namespace):
    """Gets a resource reference for the resource being operated on.

    Args:
      namespace: The argparse namespace.

    Returns:
      resources.Resource, The parsed resource reference.
    """
    return self._ParseResourceArg(namespace)

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
        params=parent_ref.AsDict())

  def _GenerateListMethodFlags(self):
    """Generates all the CLI flags for a List command.

    Returns:
      {str, calliope.base.Action}, A map of field name to the argument.
    """
    flags = {}
    if not self.raw and self.method.IsList():
      flags[base.FILTER_FLAG.name] = base.FILTER_FLAG
      flags[base.SORT_BY_FLAG.name] = base.SORT_BY_FLAG
      if self.method.IsPageableList() and self.method.ListItemField():
        # We can use YieldFromList() with a limit.
        flags[base.LIMIT_FLAG.name] = base.LIMIT_FLAG
        if self.method.BatchPageSizeField():
          # API supports page size.
          flags[base.PAGE_SIZE_FLAG.name] = base.PAGE_SIZE_FLAG
    return flags

  def Limit(self, namespace):
    """Gets the value of the limit flag (if present)."""
    if (not self.raw and
        self.method.IsPageableList() and
        self.method.ListItemField()):
      return getattr(namespace, 'limit')

  def PageSize(self, namespace):
    """Gets the value of the page size flag (if present)."""
    if (not self.raw and
        self.method.IsPageableList() and
        self.method.ListItemField() and
        self.method.BatchPageSizeField()):
      return getattr(namespace, 'page_size')

  def _GenerateResourceArg(self):
    """Gets the flags to add to the parser that appear in the method path.

    Returns:
      {str, calliope.base.Argument}, A map of field name to argument.
    """
    field_names = self.method.ResourceFieldNames()
    if not field_names:
      return {}

    message = self.method.GetRequestType()
    field_helps = _FieldHelpDocs(message)
    default_help = 'For substitution into: ' + self.method.detailed_path

    args = {}
    if not self.clean_surface:
      # Make a dedicated positional in addition to the flags for each part of
      # the URI path.
      args[ArgumentGenerator.FLAT_RESOURCE_ARG_NAME] = base.Argument(
          ArgumentGenerator.FLAT_RESOURCE_ARG_NAME,
          nargs='?',
          help='The GRI for the resource being operated on.')

    anchor_arg_name = self._GetArgAttributes(
        field_names[-1], required=True).arg_name

    for field in field_names:
      attributes = self._GetArgAttributes(field, field_helps, default_help,
                                          required=True)
      param = attributes.arg_name
      # If the request params match, this means this method takes the same
      # params as the get method and so the last item should be positional.
      # If it doesn't (like for a list command) then we are omitting the last
      # arg so all other should be flags and none should be made positional.
      is_positional = (self.clean_surface and param == anchor_arg_name
                       and self.method.request_params_match_resource)
      args[param] = base.Argument(
          param if is_positional else '--' + param,
          metavar=resource_property.ConvertToAngrySnakeCase(param),
          # TODO(b/64147277): Usage a proper arg group to make the positional
          # and flags for the resource argument show up together.
          # category=(None if param == self.anchor_arg_name and
          # self.is_positional else 'RESOURCE'),
          type=attributes.type or str,
          completer=attributes.completer,
          help=attributes.help_text)
      if (self.clean_surface and param == anchor_arg_name and
          not is_positional):
        args[param].kwargs['required'] = True
    return args

  def _ParseResourceArg(self, namespace):
    """Gets the resource ref for the resource specified as the positional arg.

    Args:
      namespace: The argparse namespace.

    Returns:
      The parsed resource ref or None if no resource arg was generated for this
      method.
    """
    field_names = self.method.ResourceFieldNames()
    if not field_names:
      return

    anchor_attr = self._GetArgAttributes(field_names[-1], required=True)
    r = (getattr(namespace, anchor_attr.arg_name) if self.clean_surface else
         getattr(namespace, ArgumentGenerator.FLAT_RESOURCE_ARG_NAME))
    if anchor_attr.processor:
      r = anchor_attr.processor(r)

    params = {}
    for f in field_names:
      attr = self._GetArgAttributes(f, required=True)
      value = getattr(namespace, attr.arg_name)
      if attr.processor:
        value = attr.processor(value)
      params[f] = value or DEFAULT_PARAMS.get(attr.arg_name, lambda: None)()

    return resources.REGISTRY.Parse(
        r,
        collection=self.method.RequestCollection().full_name,
        params=params)

  def _GenerateMessageFieldsFlags(self, prefix, message, groups=None,
                                  is_root=True):
    """Gets the arguments to add to the parser that appear in the method body.

    Args:
      prefix: str, A string to prepend to the name of the flag. This is used
        for flags representing fields of a submessage.
      message: The apitools message to generate the flags for.
      groups: {id: calliope.base.ArgumentGroup}, The collection of groups that
        have been generated. Newly generated arguments will be put in one of
        these groups if their attributes say they should be. This collection
        is modified and should not be passed in at the root invocation.
      is_root: bool, True if this is the request message itself (not a
        sub-field).

    Returns:
      {str, calliope.base.Argument}, A map of field name to argument.
    """
    args = {}
    if groups is None:
      groups = {}
    field_helps = _FieldHelpDocs(message)
    for field in message.all_fields():
      attributes = self._FlagAttributesForField(prefix, field, is_root)
      if not attributes:
        continue
      name = attributes.arg_name
      if (field.variant == messages.Variant.MESSAGE and
          (self.arg_info is None or prefix + field.name not in self.arg_info)):
        sub_args = self._GenerateMessageFieldsFlags(
            name + '.', field.type, groups, is_root=False)
        if self.arg_info is not None:
          args.update(sub_args)
        elif sub_args:
          field_help = field_helps.get(field.name, None)
          group = base.ArgumentGroup(
              name,
              description=(name + ': ' + field_help) if field_help else '')
          for arg in sub_args.values():
            group.AddArgument(arg)
          args[name] = group
      else:
        args[name] = self._MaybeAddArgToGroup(
            attributes,
            self._GenerateMessageFieldFlag(attributes, prefix, field),
            groups)
    return {k: v for k, v in args.iteritems() if v is not None}

  def _MaybeAddArgToGroup(self, attributes, arg, groups):
    """Conditionally adds the argument to a group if it should be in one.

    Args:
      attributes: yaml_command_schema.Argument, The attributes to use to
        generate the arg.
      arg: calliope.base.Argument: The generated arg.
      groups: {id: calliope.base.ArgumentGroup}, The collection of groups that
        have been generated.

    Returns:
      The argument if not in a group, an ArgumentGroup if a new group was
      created for this argument, or None if it was added to a group that already
      exists.
    """
    if not attributes.group:
      # This is just a normal argument, return it so it can be added to the
      # parser.
      return arg

    group = groups.get(attributes.group.group_id, None)
    if group:
      # The group this belongs to has already been created and stored. Just add
      # this arg to the group, no need to add the group again, so return None.
      group.AddArgument(arg)
      return None

    # Arg is in a group but it hasn't been created yet. Make the group, store it
    # and return it for addition to the parser.
    group = base.ArgumentGroup(attributes.group.group_id,
                               required=attributes.group.required)
    groups[attributes.group.group_id] = group
    group.AddArgument(arg)
    return group

  def _ParseMessageFieldsFlags(self, namespace, prefix, message, static_fields,
                               is_root):
    """Recursively generates the request message and any sub-messages.

    Args:
      namespace: The argparse namespace containing the all the parsed arguments.
      prefix: str, The flag prefix for the sub-message being generated.
      message: The apitools class for the message.
      static_fields: {str, value}, A mapping of API field name to value to
        insert into the message.
      is_root: bool, True if this is the request message itself (not a
        sub-field).

    Returns:
      The instantiated apitools Message with all fields filled in from flags.
    """
    kwargs = {}
    for field in message.all_fields():
      static_value = static_fields.get(prefix + field.name, None)
      if static_value:
        kwargs[field.name] = _ConvertValue(field, static_value)

      attributes = self._FlagAttributesForField(prefix, field, is_root)
      if not attributes:
        continue
      name = attributes.arg_name
      # Field is a sub-message, recursively generate it.
      if (field.variant == messages.Variant.MESSAGE and
          (self.arg_info is None or prefix + field.name not in self.arg_info)):
        sub_kwargs = self._ParseMessageFieldsFlags(
            namespace, name + '.', field.type, static_fields, is_root=False)
        if sub_kwargs:
          # Only construct the sub-message if we have something to put in it.
          value = field.type(**sub_kwargs)
          # TODO(b/38000796): Handle repeated fields correctly.
          kwargs[field.name] = value if not field.repeated else [value]
      # Field is a scalar, just get the value.
      else:
        value = getattr(namespace, name.replace('-', '_'), None)
        if value is not None:
          kwargs[field.name] = _ConvertValue(field, value, attributes)
    return kwargs

  def _FlagAttributesForField(self, prefix, field, is_root):
    """Compute the flag name to generate for the given message field.

    Args:
      prefix: str, A prefix to put on the flag (when generating flags for
        sub-messages).
      field: MessageField, The apitools field to generate the flag for.
      is_root: bool, True if this is the request message itself (not a
        sub-field).

    Returns:
      yaml_command_schema.Argument, The attributes to use to generate the arg,
      or None if it should not be generated.
    """
    if self._ShouldSkipAtomicField(field, is_root):
      return None
    attributes = self._GetArgAttributes(prefix + field.name)
    if not attributes:
      if field.variant == messages.Variant.MESSAGE:
        # If we are not generating this field, but it is a message, we might
        # want to generate flags for specific parts of the sub message.
        return yaml_command_schema.Argument(prefix + field.name, None)
      # Only stop processing if this is a scalar.
      return None
    if attributes.arg_name in self.ignored_fields:
      return None
    if field.variant == messages.Variant.MESSAGE:
      if (attributes.arg_name == self.method.request_field and
          attributes.arg_name.lower().endswith('request')):
        attributes.arg_name = 'request'
    return attributes

  def _ShouldSkipAtomicField(self, field, is_root):
    return (is_root and self.clean_surface and self.is_atomic
            and field.name in self.method.params)

  def _GetArgAttributes(self, field, field_helps=None, default_help=None,
                        required=False):
    """Gets attributes of the argument that should be generated.

    Args:
      field: str, The name of the field.
      field_helps: {str: str}, A mapping of field name to help strings.
      default_help: str, The help string to use if there is no specific help
        for this flag.
      required: bool, True if we must generate an arg for this field (if it is
        part of the resource arg) or false if it is ok to not generate a flag
        for it (and it will just be None in the request).

    Raises:
      MissingArgInformation: If arg info is provided but the given field was
      not registered, and it has been marked as required=True.

    Returns:
      yaml_command_schema.Argument, The attributes to use to generate the arg,
      or None if it should not be generated.
    """
    if not field_helps:
      field_helps = {}
    if self.arg_info is None:
      # No info was given, we are just auto generating everything.
      return yaml_command_schema.Argument(
          arg_name=self.auto_rename_fields.get(field, field),
          help_text=field_helps.get(field.split('.')[-1], default_help)
      )

    # Arg information was explicitly provided, so only generate fields that
    # are registered.
    data = self.arg_info.get(field)
    if data:
      return data
    if required:
      renamed = self.auto_rename_fields.get(field, field)
      if renamed not in self.builtin_args:
        # This is a resource arg and it must be registered.
        raise MissingArgInformation(field)
      # A required arg that is not registered, but is a builtin, so we don't
      # care because it won't be used. We do need to return a name here so
      # that it will end up being parsed though.
      return yaml_command_schema.Argument(
          arg_name=renamed,
          help_text=None,
      )

    # No info was provided for this arg and it is not required, don't generate.
    return None

  def _GenerateMessageFieldFlag(self, attributes, prefix, field):
    """Gets a flag for a single field in a message.

    Args:
      attributes: yaml_command_schema.Argument, The attributes to use to
        generate the arg.
      prefix: str, The flag prefix for the sub-message being generated.
      field: The apitools field object.

    Returns:
      calliope.base.Argument, The generated argument.
    """
    if _IsOutputField(attributes.help_text):
      return None
    variant = field.variant
    choices = None
    if attributes.choices is not None:
      choices = attributes.choices.keys()
    elif variant == messages.Variant.ENUM:
      choices = [_EnumNameToChoice(name) for name in field.type.names()]
    t = attributes.type or _TYPES.get(variant, None)
    action = attributes.action
    if not action:
      if variant == messages.Variant.BOOL and self.clean_surface:
        # Create proper boolean flags for declarative surfaces
        action = 'store_true'
      else:
        action = 'store'

    # Note that a field will never be a message at this point, always a scalar.
    if field.repeated:
      t = arg_parsers.ArgList(element_type=t, choices=choices)

    name = attributes.arg_name
    metavar = name
    if metavar.startswith(prefix):
      metavar = metavar[len(prefix):]
    category = None
    if self.arg_info is None and not attributes.is_positional:
      category = 'MESSAGE'
    arg = base.Argument(
        # TODO(b/38000796): Consider not using camel case for flags.
        name if attributes.is_positional else '--' + name,
        category=category,
        action=action,
        completer=attributes.completer,
        help=attributes.help_text,
        hidden=attributes.hidden,
    )
    if attributes.default is not None:
      arg.kwargs['default'] = attributes.default
    if action != 'store_true':
      # For this special action type, it won't accept a bunch of the common
      # kwargs, so we can only add them if not generating a boolean flag.
      arg.kwargs['metavar'] = resource_property.ConvertToAngrySnakeCase(
          metavar.replace('-', '_'))
      arg.kwargs['type'] = t
      arg.kwargs['choices'] = choices

    if not attributes.is_positional:
      arg.kwargs['required'] = attributes.required
    return arg


def _ConvertValue(field, value, attributes=None):
  """Coverts the parsed value into something to insert into a request message.

  If a processor is registered, that is called on the value.
  If a choices mapping was provided, each value is mapped back into its original
  value.
  If the field is an enum, the value will be looked up by name and the Enum type
  constructed.

  Args:
    field: The apitools field object.
    value: The parsed value. This must be a scalar for scalar fields and a list
      for repeated fields.
    attributes: yaml_command_schema.Argument, The attributes used to
        generate the arg.

  Returns:
    The value to insert into the message.
  """
  if attributes and attributes.processor:
    return attributes.processor(value)

  if attributes and attributes.choices:
    if field.repeated:
      value = [attributes.choices.get(v, v) for v in value]
    else:
      value = attributes.choices.get(value, value)
  if field.variant == messages.Variant.ENUM:
    t = field.type
    if field.repeated:
      return [_ChoiceToEnum(v, t) for v in value]
    return _ChoiceToEnum(value, t)
  return value


def _ChoiceToEnum(choice, enum_type):
  name = choice.replace('-', '_').upper()
  return enum_type.lookup_by_name(name)


def _FieldHelpDocs(message):
  """Gets the help text for the fields in the request message.

  Args:
    message: The apitools message.

  Returns:
    {str: str}, A mapping of field name to help text.
  """
  field_helps = {}
  current_field = None

  match = re.search(r'^\s+Fields:.*$', message.__doc__ or '', re.MULTILINE)
  if not match:
    # Couldn't find any fields at all.
    return field_helps

  for line in message.__doc__[match.end():].splitlines():
    match = re.match(r'^\s+(\w+): (.*)$', line)
    if match:
      # This line is the start of a new field.
      current_field = match.group(1)
      field_helps[current_field] = match.group(2).strip()
    elif current_field:
      # Append additional text to the in progress field.
      to_append = line.strip()
      if to_append:
        current_text = field_helps.get(current_field, '')
        field_helps[current_field] = current_text + ' ' + to_append

  return field_helps


def _IsOutputField(help_text):
  """Determines if the given field is output only based on help text."""
  return help_text and help_text.startswith('[Output Only]')
