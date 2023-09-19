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

"""Data objects to support the yaml command schema."""


from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import arg_parsers_usage_text as usage_text
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.command_lib.util.args import labels_util
from googlecloudsdk.core import module_util

import six


NAME_FORMAT_KEY = '__name__'
RESOURCE_ID_FORMAT_KEY = '__resource_id__'
REL_NAME_FORMAT_KEY = '__relative_name__'
RESOURCE_TYPE_FORMAT_KEY = '__resource_type__'


def FormatResourceAttrStr(format_string, resource_ref, display_name=None,
                          display_resource_type=None):
  """Formats a string with all the attributes of the given resource ref.

  Args:
    format_string: str, The format string.
    resource_ref: resources.Resource, The resource reference to extract
      attributes from.
    display_name: the display name for the resource.
    display_resource_type:

  Returns:
    str, The formatted string.
  """
  if resource_ref:
    d = resource_ref.AsDict()
    d[NAME_FORMAT_KEY] = (
        display_name or resource_ref.Name())
    d[RESOURCE_ID_FORMAT_KEY] = resource_ref.Name()
    d[REL_NAME_FORMAT_KEY] = resource_ref.RelativeName()
  else:
    d = {NAME_FORMAT_KEY: display_name}
  d[RESOURCE_TYPE_FORMAT_KEY] = display_resource_type

  try:
    return format_string.format(**d)
  except KeyError as err:
    if err.args:
      raise KeyError('Key [{}] does not exist. Must specify one of the '
                     'following keys instead: {}'.format(
                         err.args[0], ', '.join(d.keys())))
    else:
      raise err


class Error(Exception):
  """Base class for module errors."""
  pass


class InvalidSchemaError(Error):
  """Error for when a yaml command is malformed."""
  pass


class Hook(object):
  """Represents a Python code hook declared in the yaml spec.

  A code hook points to some python element with a module path, and attribute
  path like: package.module:class.attribute.

  If arguments are provided, first the function is called with the arguments
  and the return value of that is the hook that is used. For example:

  googlecloudsdk.calliope.arg_parsers:Duration:lower_bound=1s,upper_bound=1m
  """

  @classmethod
  def FromData(cls, data, key):
    """Gets the hook from the spec data.

    Args:
      data: The yaml spec
      key: The key to extract the hook path from.

    Returns:
      The Python element to call.
    """
    path = data.get(key)
    if path:
      return cls.FromPath(path)
    return None

  @classmethod
  def FromPath(cls, path):
    """Gets the hook from the function path.

    Args:
      path: str, The module path to the hook function.

    Returns:
      The Python element to call.
    """
    return ImportPythonHook(path).GetHook()

  def __init__(self, attribute, kwargs=None):
    self.attribute = attribute
    self.kwargs = kwargs

  def GetHook(self):
    """Gets the Python element that corresponds to this hook.

    Returns:
      A Python element.
    """
    if self.kwargs is not None:
      return  self.attribute(**self.kwargs)
    return self.attribute


def ImportPythonHook(path):
  """Imports the given python hook.

  Depending on what it is used for, a hook is a reference to a class, function,
  or attribute in Python code.

  Args:
    path: str, The path of the hook to import. It must be in the form of:
      package.module:attribute.attribute where the module path is separated from
      the class name and sub attributes by a ':'. Additionally, ":arg=value,..."
      can be appended to call the function with the given args and use the
      return value as the hook.

  Raises:
    InvalidSchemaError: If the given module or attribute cannot be loaded.

  Returns:
    Hook, the hook configuration.
  """
  parts = path.split(':')
  if len(parts) != 2 and len(parts) != 3:
    raise InvalidSchemaError(
        'Invalid Python hook: [{}]. Hooks must be in the format: '
        'package(.module)+:attribute(.attribute)*(:arg=value(,arg=value)*)?'
        .format(path))
  try:
    attr = module_util.ImportModule(parts[0] + ':' + parts[1])
  except module_util.ImportModuleError as e:
    raise InvalidSchemaError(
        'Could not import Python hook: [{}]. {}'.format(path, e))

  kwargs = None
  if len(parts) == 3:
    kwargs = {}
    for arg in parts[2].split(','):
      if not arg:
        continue
      arg_parts = arg.split('=')
      if len(arg_parts) != 2:
        raise InvalidSchemaError(
            'Invalid Python hook: [{}]. Args must be in the form arg=value,'
            'arg=value,...'.format(path))
      kwargs[arg_parts[0].strip()] = arg_parts[1].strip()

  return Hook(attr, kwargs)


STATIC_ACTIONS = {'store', 'store_true', 'append'}


def ParseAction(action, flag_name):
  """Parse the action out of the argument spec.

  Args:
    action: The argument action spec data.
    flag_name: str, The effective flag name.

  Raises:
    ValueError: If the spec is invalid.

  Returns:
    The action to use as argparse accepts it. It will either be a class that
    implements action, or it will be a str of a builtin argparse type.
  """
  if not action:
    return None

  if isinstance(action, six.string_types):
    if action in STATIC_ACTIONS:
      return action
    return Hook.FromPath(action)

  deprecation = action.get('deprecated')
  if deprecation:
    return actions.DeprecationAction(flag_name, **deprecation)

  raise ValueError('Unknown value for action: ' + six.text_type(action))


BUILTIN_TYPES = {
    'str': str,
    'int': int,
    'long': long if six.PY2 else int,  # long is referring to a type, so pylint: disable=undefined-variable
    'float': float,
    'bool': bool,
}


def ParseType(t):
  """Parse the action out of the argument spec.

  Args:
    t: The argument type spec data.

  Raises:
    ValueError: If the spec is invalid.

  Returns:
    The type to use as argparse accepts it.
  """
  if not t:
    return None

  if 'arg_object' in t:
    if isinstance(t, dict):
      data = t.get('arg_object')
    else:
      data = None
    return ArgObject.FromData(data)

  if isinstance(t, six.string_types):
    builtin_type = BUILTIN_TYPES.get(t)
    if builtin_type:
      return builtin_type
    if 'arg_list' in t:
      t = 'googlecloudsdk.calliope.arg_parsers:ArgList:'
    return Hook.FromPath(t)

  if 'arg_dict' in t:
    return ArgDict.FromData(t.get('arg_dict'))

  raise ValueError('Unknown value for type: ' + six.text_type(t))


class Choice(object):
  """Holds information about a single enum choice value."""

  def __init__(self, data):
    self.arg_value = data['arg_value']
    if isinstance(self.arg_value, six.string_types):
      # We always do a case insensitive comparison.
      self.arg_value = self.arg_value.lower()
    if 'enum_value' in data:
      self.enum_value = data['enum_value']
    else:
      self.enum_value = arg_utils.ChoiceToEnumName(self.arg_value)
    self.help_text = data.get('help_text')

  @classmethod
  def ToChoiceMap(cls, choices):
    """Converts a list of choices into a map for easy value lookup.

    Args:
      choices: [Choice], The choices.

    Returns:
      {arg_value: enum_value}, A mapping of user input to the value that should
      be used. All arg_values have already been converted to lowercase for
      comparison.
    """
    if not choices:
      return {}
    return {c.arg_value: c.enum_value for c in choices}


def _SetFieldInMessage(message_instance, field_spec, value):
  if value is None and field_spec.repeated:
    value = []
  arg_utils.SetFieldInMessage(message_instance, field_spec.api_field, value)


def _ParseFieldsIntoMessage(field_dict, message, field_specs):
  """Iterates through fields and adds fields to message instance.

  Args:
    field_dict: [str: apitools field], dictionary of the cli name to
      the apitools field instance
    message: apitools message class
    field_specs: [SpecField], list of the fields to parse into message instance

  Returns:
    Instance of apitools message with the fields parsed into the message.
  """
  message_instance = message()
  for f in field_specs:
    value = field_dict.get(f.arg_name)
    _SetFieldInMessage(message_instance, f, value)
  return message_instance


class _FieldType(usage_text.DefaultArgTypeWrapper):
  """Type that converts string into apitools field instance.

  Attributes:
    field: apitools field instance
    field_spec: SpecField, specifies type of the field we are creating
  """

  def __init__(self, arg_type, field, field_spec):
    super(_FieldType, self).__init__(arg_type)
    self.field = field
    self.field_spec = field_spec

  def __call__(self, arg_value):
    parsed_arg_value = super(_FieldType, self).__call__(arg_value)
    return arg_utils.ConvertValue(
        self.field, parsed_arg_value, repeated=self.field_spec.repeated,
        choices=self.field_spec.ChoiceMap())


class _MessageFieldType(usage_text.DefaultArgTypeWrapper):
  """Type that converts string input into apitools message.

  Attributes:
    message_cls: apitools message class
    field_specs: [SpecField], list fields that need to be parsed into
      each apitools message instance
  """

  def __init__(self, arg_type, message_cls, field_specs):
    super(_MessageFieldType, self).__init__(arg_type)
    self.message_cls = message_cls
    self.field_specs = field_specs

  def __call__(self, arg_value):
    parsed_arg_value = super(_MessageFieldType, self).__call__(arg_value)
    if isinstance(parsed_arg_value, list):
      return [
          _ParseFieldsIntoMessage(r, self.message_cls, self.field_specs)
          for r in parsed_arg_value]

    return _ParseFieldsIntoMessage(
        parsed_arg_value, self.message_cls, self.field_specs)


class _MapFieldType(usage_text.DefaultArgTypeWrapper):
  """Type converts string into list of apitools message instances for map field.

  Type function returns a list of apitools messages with key, value fields ie
  [Message(key=key1, value=value1), Message(key=key2, value=value2), etc].
  The list of messages is how apitools specifies map fields.

  Attributes:
    message_cls: apitools message class
    key_spec: SpecField, specifes expected type of key field
    value_spec: SpecField, specifies expected type of value field

  Returns:
    function that parses arg_value (str) and returns list of apitools messages
      with key value fields ie
      [Message(key=key1, value=value1), Message(key=key2, value=value2), etc]
  """

  def __init__(self, arg_type, message_cls, key_spec, value_spec):
    super(_MapFieldType, self).__init__(arg_type)
    self.message_cls = message_cls
    self.key_spec = key_spec
    self.value_spec = value_spec

  def __call__(self, arg_value):
    parsed_arg_value = super(_MapFieldType, self).__call__(arg_value)
    messages = []
    # NOTE: While repeating fields and messages are accounted for, repeating
    # maps are not. This is because repeating map fields are not allowed in
    # proto definitions. Result will never be a list of dictionaries.
    for k, v in sorted(six.iteritems(parsed_arg_value)):
      message_instance = self.message_cls()
      _SetFieldInMessage(message_instance, self.key_spec, k)
      _SetFieldInMessage(message_instance, self.value_spec, v)
      messages.append(message_instance)
    return messages


class _AdditionalPropsType(usage_text.DefaultArgTypeWrapper):
  """Type converts string into apitools additional props field instance.

  Attributes:
    field: apitools field instance
  """

  def __init__(self, arg_type, field):
    super(_AdditionalPropsType, self).__init__(arg_type)
    self.field = field

  def __call__(self, arg_value):
    additional_props = super(_AdditionalPropsType, self).__call__(arg_value)
    parent_message = self.field.type()
    arg_utils.SetFieldInMessage(
        parent_message, arg_utils.ADDITIONAL_PROPS, additional_props)
    return parent_message


def _GetSimpleFieldType(message, field_spec):
  """Retrieves the the type of the field from message.

  Args:
    message: Apitools message class
    field_spec: SpecField, specifies the api field

  Returns:
    type function or apitools field class

  Raises:
    InvalidSchemaError: if the field type is not listed in arg_utils.TYPES
  """
  f = arg_utils.GetFieldFromMessage(message, field_spec.api_field)
  t = field_spec.field_type or arg_utils.TYPES.get(f.variant)

  if not t:
    raise InvalidSchemaError('Unknown type for field: ' + field_spec.api_field)

  return _FieldType(t, f, field_spec)


class ArgObject(arg_utils.ArgObjectType):
  """A wrapper to bind an ArgObject argument to a message or field."""

  @classmethod
  def FromData(cls, unused_data=None):
    """Creates ArgObject from yaml data."""
    # TODO(b/278780718) parse spec data that can be specifed by the user
    return cls()

  def __init__(self, arg_type=None, help_text=None):
    self.arg_type = arg_type
    self.help_text = help_text

  def Action(self, field):
    """Returns the correct argument action.

    Args:
      field: apitools field instance

    Returns:
      str, argument action string.
    """
    if field.repeated:
      return arg_parsers.FlattenAction()
    return 'store'

  def _GetFieldType(self, message, field_spec):
    """Retrieves the the type of the field from messsage.

    Args:
      message: Apitools message class
      field_spec: SpecField, specifies the api field

    Returns:
      type function or apitools class for the message field
    """
    f = arg_utils.GetFieldFromMessage(message, field_spec.api_field)
    arg_obj = ArgObject(
        arg_type=field_spec.field_type, help_text=field_spec.help_text)
    return arg_obj.GenerateType(f, is_root=False)

  def _GenerateMapType(self, field, is_root=True):
    """Returns function that parses apitools map fields from string.

    Map fields are proto fields with type `map<...>` that generate
    apitools message with an additionalProperties field

    Args:
      field: apitools field instance
      is_root: whether the type function is for the root level of the message

    Returns:
      type function that takes string like 'foo=bar' or '{"foo": "bar"}' and
        creates an apitools message additionalProperties field
    """
    try:
      additional_props_field = arg_utils.GetFieldFromMessage(
          field.type, arg_utils.ADDITIONAL_PROPS)
    except arg_utils.UnknownFieldError:
      raise InvalidSchemaError(
          '{name} message does not contain field "{props}". Remove '
          '"{props}" from api field name.'.format(
              name=field.name,
              props=arg_utils.ADDITIONAL_PROPS
          ))

    # TODO(b/278780718) allow spec data to specify the key, value fields

    # Add some default validation and help text for labels fields
    if field.name == 'labels':
      key_type = labels_util.KEY_FORMAT_VALIDATOR
      key_help = labels_util.KEY_FORMAT_HELP
      value_type = labels_util.VALUE_FORMAT_VALIDATOR
      value_help = labels_util.VALUE_FORMAT_HELP
    else:
      key_type, key_help = None, None
      value_type, value_help = None, None

    key_spec = SpecField.FromField(
        arg_utils.GetFieldFromMessage(additional_props_field.type, 'key'),
        field_type=key_type, help_text=key_help)
    value_spec = SpecField.FromField(
        arg_utils.GetFieldFromMessage(additional_props_field.type, 'value'),
        field_type=value_type, help_text=value_help)

    key_type = self._GetFieldType(additional_props_field.type, key_spec)
    value_type = self._GetFieldType(additional_props_field.type, value_spec)

    arg_obj = arg_parsers.ArgObject(
        key_type=key_type,
        value_type=value_type,
        help_text=self.help_text,
        enable_shorthand=is_root)
    map_type = _MapFieldType(
        arg_obj, additional_props_field.type, key_spec, value_spec)

    # Uses an additional type function to map additionalProperties back into
    # parent map message
    return _AdditionalPropsType(map_type, field)

  def _GenerateMessageType(self, field, is_root=True):
    """Returns function that parses apitools message fields from string.

    Args:
      field: apitools field instance
      is_root: whether the type function is for the root level of the message

    Returns:
      type function that takes string like 'foo=bar' or '{"foo": "bar"}' and
        creates an apitools message like Message(foo=bar) or [Message(foo=bar)]
    """
    apitools_fields = field.type.all_fields()
    output_only_fields = {'createTime', 'updateTime'}

    # TODO(b/278780718) allow spec data to specify the message fields
    field_specs = [
        SpecField.FromField(f)
        for f in apitools_fields if f.name not in output_only_fields
    ]

    spec = {f.arg_name: self._GetFieldType(field.type, f) for f in field_specs}
    required = [f.arg_name for f in field_specs if f.required]
    arg_obj = arg_parsers.ArgObject(spec=spec,
                                    help_text=self.help_text,
                                    required_keys=required,
                                    repeated=field.repeated,
                                    enable_shorthand=is_root)

    return _MessageFieldType(arg_obj, field.type, field_specs)

  def _GenerateFieldType(self, field):
    """Returns function that parses apitools field from string.

    Args:
      field: apitools field instance

    Returns:
      type function that takes string like '1' or ['1'] and parses it
        into 1 or [1] depending on the apitools field type
    """
    # TODO(b/278780718) allow spec data to specify the field type
    field_spec = SpecField.FromField(
        field, help_text=self.help_text, field_type=self.arg_type)
    arg_obj = arg_parsers.ArgObject(
        value_type=field_spec.field_type,
        help_text=field_spec.help_text,
        repeated=field_spec.repeated,
        enable_shorthand=False
    )
    return _FieldType(arg_obj, field, field_spec)

  def GenerateType(self, field, is_root=True):
    """Generates an argparse type function to use to parse the argument.

    Args:
      field: apitools field instance we are generating ArgObject for
      is_root: bool, whether this is the first level of the ArgObject
        we are generating for.

    Returns:
        Type function that returns apitools message instance or list
          of instances.
    """
    field_type = arg_utils.GetFieldType(field)
    if field_type == arg_utils.FieldType.MAP:
      return self._GenerateMapType(field, is_root)
    # TODO(b/286379489): add parsing logic for cyclical fields
    if field_type == arg_utils.FieldType.MESSAGE:
      return self._GenerateMessageType(field, is_root)
    return self._GenerateFieldType(field)


class ArgDict(arg_utils.RepeatedMessageBindableType):
  """A wrapper to bind an ArgDict argument to a message.

  The non-flat mode has one dict per message. When the field is repeated, you
  can repeat the message by repeating the flag. For example, given a message
  with fields foo and bar, it looks like:

  --arg foo=1,bar=2 --arg foo=3,bar=4

  The Action method below is used later during argument generation to tell
  argparse to allow repeats of the dictionary and to append them.
  """

  @classmethod
  def FromData(cls, data):
    fields = [SpecField.FromData(d) for d in data['spec']]
    if data.get('flatten'):
      if len(fields) != 2:
        raise InvalidSchemaError(
            'Flattened ArgDicts must have exactly two items in the spec.')
      return FlattenedArgDict(fields[0], fields[1])
    return cls(fields)

  def __init__(self, fields):
    self.fields = fields

  def Action(self):
    return 'append'

  def GenerateType(self, message):
    """Generates an argparse type function to use to parse the argument.

    The return of the type function will be an instance of the given message
    with the fields filled in.

    Args:
      message: The apitools message class.

    Raises:
      InvalidSchemaError: If a type for a field could not be determined.

    Returns:
      f(str) -> message, The type function that parses the ArgDict and returns
      a message instance.
    """
    spec = {f.arg_name: _GetSimpleFieldType(message, f) for f in self.fields}

    required = [f.arg_name for f in self.fields if f.required]
    arg_dict = arg_parsers.ArgDict(spec=spec, required_keys=required)
    return _MessageFieldType(arg_dict, message, self.fields)


class FlattenedArgDict(arg_utils.RepeatedMessageBindableType):
  """A wrapper to bind an ArgDict argument to a message with a key/value pair.

  The flat mode has one dict corresponding to a repeated field. For example,
  given a message with fields key and value, it looks like:

  --arg a=b,c=d

  Which would generate 2 instances of the message:
  [{key=a, value=b}, {key=c, value=d}]
  """

  def __init__(self, key_field, value_field):
    self.key_spec = key_field
    self.value_spec = value_field

  def GenerateType(self, message):
    """Generates an argparse type function to use to parse the argument.

    The return of the type function will be a list of instances of the given
    message with the fields filled in.

    Args:
      message: The apitools message class.

    Raises:
      InvalidSchemaError: If a type for a field could not be determined.

    Returns:
      f(str) -> [message], The type function that parses the ArgDict and returns
      a list of message instances.
    """
    key_type = _GetSimpleFieldType(message, self.key_spec)
    value_type = _GetSimpleFieldType(message, self.value_spec)
    arg_dict = arg_parsers.ArgDict(key_type=key_type, value_type=value_type)

    return _MapFieldType(
        arg_dict, message, self.key_spec, self.value_spec)


class SpecField(object):
  """Attributes about the fields that make up an ArgDict spec.

  Attributes:
    api_field: The name of the field under the repeated message that the value
      should be put.
    arg_name: The name of the key in the dict.
    field_type: The argparse type of the value of this field.
    repeated: Whether the field is a repeated field
    required: True if the key is required.
    choices: A static map of choice to value the user types.
    help_text: Help text associated with the field
  """

  @classmethod
  def FromData(cls, data):
    api_field = data['api_field']
    data_choices = data.get('choices')
    choices = [Choice(d) for d in data_choices] if data_choices else None
    return cls(
        api_field=api_field,
        arg_name=data.get('arg_name', api_field),
        field_type=ParseType(data.get('type')),
        repeated=data.get('repeated', False),
        required=data.get('required', True),
        choices=choices,
        help_text=None
    )

  @classmethod
  def FromField(cls, field, field_type=None, help_text=None):
    return cls(
        api_field=field.name,
        arg_name=field.name,
        field_type=field_type or arg_utils.TYPES.get(field.variant),
        required=field.required,
        repeated=field.repeated,
        choices=None,
        help_text=help_text,
    )

  def __init__(self, api_field, arg_name, field_type, repeated, required,
               choices, help_text):
    self.api_field = api_field
    self.arg_name = arg_name
    self.field_type = field_type
    self.repeated = repeated
    self.required = required
    self.choices = choices
    self.help_text = help_text

  def ChoiceMap(self):
    return Choice.ToChoiceMap(self.choices)
