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
from collections import OrderedDict
import re

from apitools.base.protorpclite import messages
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.core import properties
from googlecloudsdk.core.resource import resource_property


class Error(Exception):
  """Base exception for this module."""
  pass


class UnknownFieldError(Error):
  """The referenced field could not be found in the message object."""

  def __init__(self, field_name, message):
    super(UnknownFieldError, self).__init__(
        'Field [{}] not found in message [{}]. Available fields: [{}]'
        .format(field_name, message.__name__,
                ', '.join(f.name for f in message.all_fields())))


def GetFieldFromMessage(message, field_path):
  """Digs into the given message to extract the dotted field.

  If the field does not exist, and error is logged.

  Args:
    message: The apitools message to dig into.
    field_path: str, The dotted path of attributes and sub-attributes.

  Returns:
    The Field type.
  """
  fields = field_path.split('.')
  for f in fields[:-1]:
    message = _GetField(message, f).type
  return _GetField(message, fields[-1])


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
    is_repeated = _GetField(message, f).repeated
    if not sub_message:
      sub_message = _GetField(message, f).type()
      if is_repeated:
        sub_message = [sub_message]
      setattr(message, f, sub_message)
    message = sub_message[0] if is_repeated else sub_message
  setattr(message, fields[-1], value)


def _GetField(message, field_name):
  try:
    return message.field_by_name(field_name)
  except KeyError:
    raise UnknownFieldError(field_name, message)


# TODO(b/64147277): Pass this down from the generator, don't hard code.
DEFAULT_PARAMS = {'project': properties.VALUES.core.project.Get,
                  'projectId': properties.VALUES.core.project.Get,
                  'projectsId': properties.VALUES.core.project.Get,
                 }


def GetFromNamespace(namespace, arg_name, fallback=None, use_defaults=False):
  """Gets the given argument from the namespace."""
  value = getattr(namespace, arg_name.replace('-', '_'), None)
  if not value and fallback:
    value = fallback()
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
  variant = field.variant if field else None
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
  # pylint: disable=g-explicit-bool-comparison, only an explicit False should
  # override this, None just means to do the default.
  if (field and field.repeated) and attributes.repeated != False:
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
  # pylint: disable=g-explicit-bool-comparison, only an explicit False should
  # override this, None just means to do the default.
  arg_repeated = field.repeated and (not attributes or
                                     attributes.repeated != False)

  if attributes and attributes.processor:
    value = attributes.processor(value)
  else:
    if attributes and attributes.choices:
      if arg_repeated:
        value = [attributes.choices.get(v, v) for v in value]
      else:
        value = attributes.choices.get(value, value)
    if field.variant == messages.Variant.ENUM:
      t = field.type
      if arg_repeated:
        value = [ChoiceToEnum(v, t) for v in value]
      else:
        value = ChoiceToEnum(value, t)

  if field.repeated and not arg_repeated:
    # If we manually made this arg singular, but it is actually a repeated field
    # wrap it in a list.
    value = [value]
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


class ChoiceEnumMapper(object):
  """Utility class for mapping apitools Enum messages to argparse choice args.

  Dynamically builds a base.Argument from an enum message.
  Derives choice values from supplied enum or an optional custom_mapping dict
  (see below).

  Class Attributes:
   choices: Either a list of strings [str] specifying the commandline choice
       values or an ordered dict of choice value to choice help string mappings
       {str -> str}
   enum: underlying enum whos values map to supplied choices.
   choice_arg: base.Argument object
   choice_mappings: Mapping of argparse choice value strings to enum values.
   custom_mappings: Optional dict mapping enum values to a custom
     argparse choice value. To maintain compatiblity with base.ChoiceAgrument(),
     dict can be either:
     {str-> str} - Enum String value to choice argument value i.e.
     {'MY_MUCH_LONGER_ENUM_VALUE':'short-arg'}
     OR
     {str -> (str, str)} -  Enum string value to  tuple of
     (choice argument value, choice help string) i.e.
     {'MY_MUCH_LONGER_ENUM_VALUE':('short-arg','My short arg help text.')}
  """
  _CUSTOM_MAPPING_ERROR = ('custom_mappings must be a dict of enum string '
                           'values to argparse argument choices. Choices must '
                           'be either a string or a string tuple of (choice, '
                           'choice_help_text): [{}]')

  def __init__(self,
               arg_name,
               message_enum,
               custom_mappings=None,
               help_str=None,
               required=False,
               action=None,
               metavar=None,
               dest=None,
               default=None):
    """Initialize ChoiceEnumMapper.

    Args:
      arg_name: str, The name of the argparse argument to create
      message_enum: apitools.Enum, the enum to map
      custom_mappings: See Above.
      help_str: string, pass through for base.Argument,
        see base.ChoiceArgument().
      required: boolean,string, pass through for base.Argument,
          see base.ChoiceArgument().
      action: string or argparse.Action, string, pass through for base.Argument,
          see base.ChoiceArgument().
      metavar: string,  string, pass through for base.Argument,
          see base.ChoiceArgument()..
      dest: string, string, pass through for base.Argument,
          see base.ChoiceArgument().
      default: string, string, pass through for base.Argument,
          see base.ChoiceArgument().

    Raises:
      ValueError: If no enum is given, mappings are incomplete
      TypeError: If invalid values are passed for base.Argument or
       custom_mapping
    """
     # pylint:disable=protected-access
    if not isinstance(message_enum, messages._EnumClass):
      raise ValueError('Invalid Message Enum: [{}]'.format(message_enum))
    self._arg_name = arg_name
    self._enum = message_enum
    self._custom_mappings = custom_mappings
    self._ValidateAndParseMappings()
    self._choice_arg = base.ChoiceArgument(
        arg_name,
        self.choices,
        help_str=help_str,
        required=required,
        action=action,
        metavar=metavar,
        dest=dest,
        default=default)

  def _ValidateAndParseMappings(self):
    """Validates and parses choice to enum mappings.

    Validates and parses choice to enum mappings including any custom mappings.

    Raises:
      ValueError: custom_mappings does not contain correct number of mapped
        values.
      TypeError: custom_mappings is incorrect type or contains incorrect types
        for mapped values.
    """
    if self._custom_mappings:  # Process Custom Mappings
      if not isinstance(self._custom_mappings, dict):
        raise TypeError(
            self._CUSTOM_MAPPING_ERROR.format(self._custom_mappings))
      enum_strings = set([x.name for x in self._enum])
      diff = set(self._custom_mappings.keys()) - enum_strings
      if diff:
        raise ValueError('custom_mappings [{}] may only contain mappings'
                         ' for enum values. invalid values:[{}]'.format(
                             ', '.join(self._custom_mappings.keys()),
                             ', '.join(diff)))
      try:
        self._ParseCustomMappingsFromTuples()
      except (TypeError, ValueError):
        self._ParseCustomMappingsFromStrings()

    else:  # No Custom Mappings so do automagic mapping
      self._choice_to_enum = {
          EnumNameToChoice(x.name): x
          for x in self._enum
      }
      self._enum_to_choice = {
          y.name: x
          for x, y in self._choice_to_enum.iteritems()
      }
      self._choices = sorted(self._choice_to_enum.keys())

  def _ParseCustomMappingsFromTuples(self):
    """Parses choice to enum mappings from custom_mapping with tuples.

     Parses choice mappings from dict mapping Enum strings to a tuple of
     choice values and choice help {str -> (str, str)} mapping.

    Raises:
      TypeError - Custom choices are not not valid (str,str) tuples.
    """
    self._choice_to_enum = {}
    self._enum_to_choice = {}
    self._choices = OrderedDict()
    for enum_string, (choice, help_str) in sorted(
        self._custom_mappings.iteritems()):
      self._choice_to_enum[choice] = self._enum(enum_string)
      self._enum_to_choice[enum_string] = choice
      self._choices[choice] = help_str

  def _ParseCustomMappingsFromStrings(self):
    """Parses choice to enum mappings from custom_mapping with strings.

     Parses choice mappings from dict mapping Enum strings to choice
     values {str -> str} mapping.

    Raises:
      TypeError - Custom choices are not strings
    """
    self._choice_to_enum = {}
    self._choices = []

    for enum_string, choice_string in sorted(self._custom_mappings.iteritems()):
      if not isinstance(choice_string, basestring):
        raise TypeError(
            self._CUSTOM_MAPPING_ERROR.format(self._custom_mappings))
      self._choice_to_enum[choice_string] = self._enum(enum_string)
      self._choices.append(choice_string)
    self._enum_to_choice = self._custom_mappings

  def GetChoiceForEnum(self, enum_value):
    """Converts an enum value to a choice argument value."""
    return self._enum_to_choice.get(str(enum_value))

  def GetEnumForChoice(self, choice_value):
    """Converts a mapped string choice value to an enum."""
    return self._choice_to_enum.get(choice_value)

  @property
  def choices(self):
    return self._choices

  @property
  def enum(self):
    return self._enum

  @property
  def choice_arg(self):
    return self._choice_arg

  @property
  def choice_mappings(self):
    return self._choice_to_enum

  @property
  def custom_mappings(self):
    return self._custom_mappings
