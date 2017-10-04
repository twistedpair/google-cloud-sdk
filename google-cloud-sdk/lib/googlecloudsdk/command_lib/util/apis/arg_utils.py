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

"""Utilities for generating and parsing arguments from API fields."""

import re

from apitools.base.protorpclite import messages
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.core import properties
from googlecloudsdk.core.resource import resource_property


def GetFieldFromMessage(message, field_path):
  """Digs into the given message to extract the dotted field.

  If the field does not exist, and error is logged.

  Args:
    message: The apitools message to dig into.
    field_path: str, The dotted path of attributes and sub-attributes.

  Returns:
    The Field type or None if that attribute does not exist.
  """
  fields = field_path.split('.')
  for f in fields[:-1]:
    message = message.field_by_name(f).type
  return message.field_by_name(fields[-1])


def SetFieldInMessage(message, field_path, value):
  """Sets the given field field in the message object.

  Args:
    message: A constructed apitools message object to inject the value into.
    field_path: str, The dotted path of attributes and sub-attributes.
    value: The value to set.
  """
  fields = field_path.split('.')
  for f in fields[:-1]:
    sub_message = getattr(message, f)
    is_repeated = message.field_by_name(f).repeated
    if not sub_message:
      sub_message = message.field_by_name(f).type()
      if is_repeated:
        sub_message = [sub_message]
      setattr(message, f, sub_message)
    message = sub_message[0] if is_repeated else sub_message
  setattr(message, fields[-1], value)


# TODO(b/64147277): Pass this down from the generator, don't hard code.
DEFAULT_PARAMS = {'project': properties.VALUES.core.project.Get,
                  'projectId': properties.VALUES.core.project.Get,
                  'projectsId': properties.VALUES.core.project.Get,
                 }


def GetFromNamespace(namespace, arg_name, use_defaults=False):
  """Gets the given argument from the namespace."""
  value = getattr(namespace, arg_name.replace('-', '_'), None)
  if not value and use_defaults:
    value = DEFAULT_PARAMS.get(arg_name, lambda: None)()
  return value


def Limit(method, namespace):
  """Gets the value of the limit flag (if present)."""
  if method.IsPageableList() and method.ListItemField():
    return getattr(namespace, 'limit')


def PageSize(method, namespace):
  """Gets the value of the page size flag (if present)."""
  if (method.IsPageableList() and method.ListItemField() and
      method.BatchPageSizeField()):
    return getattr(namespace, 'page_size')


def GenerateFlag(field, attributes, fix_bools=True, category=None):
  """Generates a flag for a single field in a message.

  Args:
    field: The apitools field object.
    attributes: yaml_command_schema.Argument, The attributes to use to
      generate the arg.
    fix_bools: True to generate boolean flags as switches that take a value or
      False to just generate them as regular string flags.
    category: The help category to put the flag in.

  Returns:
    calliope.base.Argument, The generated argument.
  """
  variant = field.variant
  t = attributes.type or TYPES.get(variant, None)

  choices = None
  if attributes.choices is not None:
    choices = sorted(attributes.choices.keys())
  elif variant == messages.Variant.ENUM:
    choices = [EnumNameToChoice(name) for name in sorted(field.type.names())]

  action = attributes.action
  if fix_bools and not action and variant == messages.Variant.BOOL:
    action = 'store_true'

  # Note that a field will never be a message at this point, always a scalar.
  if field.repeated:
    t = arg_parsers.ArgList(element_type=t, choices=choices)
  name = attributes.arg_name
  arg = base.Argument(
      # TODO(b/38000796): Consider not using camel case for flags.
      name if attributes.is_positional else '--' + name,
      category=category if not attributes.is_positional else None,
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
    metavar = attributes.metavar or name
    arg.kwargs['metavar'] = resource_property.ConvertToAngrySnakeCase(
        metavar.replace('-', '_'))
    arg.kwargs['type'] = t
    arg.kwargs['choices'] = choices

  if not attributes.is_positional:
    arg.kwargs['required'] = attributes.required
  return arg


def ConvertValue(field, value, attributes=None):
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
      return [ChoiceToEnum(v, t) for v in value]
    return ChoiceToEnum(value, t)
  return value


def ChoiceToEnum(choice, enum_type):
  """Converts the typed choice into an apitools Enum value."""
  name = choice.replace('-', '_').upper()
  return enum_type.lookup_by_name(name)


def EnumNameToChoice(name):
  """Converts the name of an Enum value into a typeable choice."""
  return name.replace('_', '-').lower()


TYPES = {
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
    # always compare against lowercase enum choices.
    messages.Variant.ENUM: EnumNameToChoice,
    messages.Variant.MESSAGE: None,
}


def FieldHelpDocs(message):
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


def IsOutputField(help_text):
  """Determines if the given field is output only based on help text."""
  return help_text and help_text.startswith('[Output Only]')
