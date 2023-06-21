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
"""Utilities for creating/parsing update argument groups."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc
import enum

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.command_lib.util.apis import yaml_command_schema_util as util

import six


# TODO(b/280653078) The UX is still under review. These utilities are
# liable to change and should not be used in new surface yet.

# TODO(b/283949482): Place this file in util/args and replace the duplicate
# logic in the util files.


class FlagType(enum.Enum):
  SET = 'set'
  CLEAR = 'clear'
  UPDATE = 'update'
  REMOVE = 'remove'


class UpdateArgumentGenerator(six.with_metaclass(abc.ABCMeta, object)):
  """Update flag generator."""

  @classmethod
  def FromArgData(cls, arg_data, message, flags_to_generate=None):
    """Creates a flag generator from yaml arg data and request message.

    Args:
      arg_data: yaml_arg_schema.Argument, data about flag being generated
      message: apitools request message object.
      flags_to_generate: [FlagType], list of flags to generate. Defaults to all

    Returns:
      UpdateArgumentGenerator, the correct version of flag generator
    """
    field = arg_utils.GetFieldFromMessage(message, arg_data.api_field)
    flag_type, action = arg_utils.GenerateFlagType(field, arg_data)

    is_repeated = field.repeated
    field_type = arg_utils.GetFieldType(field)

    if field_type == arg_utils.FieldType.MAP:
      gen_cls = UpdateMapArgumentGenerator
    elif is_repeated:
      gen_cls = UpdateListArgumentGenerator
    else:
      gen_cls = UpdateDefaultArgumentGenerator

    return gen_cls(arg_data.arg_name, field, flag_type, action, arg_data.hidden,
                   arg_data.help_text, arg_data.api_field, arg_data.repeated,
                   arg_data.processor, arg_data.choices, flags_to_generate)

  def __init__(self, arg_name, field, flag_type, action, is_hidden, help_text,
               api_field, repeated, processor, choices, flags_to_generate):
    self.arg_name = arg_name
    if self.arg_name.startswith('--'):
      self.arg_name = self.arg_name[2:]

    self.field = field
    self.flag_type = flag_type
    self.action = action
    self.is_hidden = is_hidden
    self.help_text = help_text
    self.api_field = api_field
    self.repeated = repeated
    self.processor = processor
    self.choices = choices

    if flags_to_generate is None:
      self.flags_to_generate = {
          FlagType.SET, FlagType.CLEAR, FlagType.UPDATE, FlagType.REMOVE}
    else:
      self.flags_to_generate = flags_to_generate

  def _GetHelpText(self, flag_type):
    return self._help_text[flag_type]

  @property
  @abc.abstractmethod
  def _help_text(self):
    """Dictionary of help text for each flag type."""
    pass

  @property
  @abc.abstractmethod
  def _flags_to_process(self):
    """Set of flag types that need to be converted."""
    pass

  @property
  def set_arg(self):
    """Flag that sets field to specifed value."""
    return base.Argument(
        '--{}'.format(self.arg_name),
        type=self.flag_type,
        action=self.action,
        help=self._GetHelpText(FlagType.SET))

  @property
  def clear_arg(self):
    """Flag that clears field."""
    return base.Argument(
        '--clear-{}'.format(self.arg_name),
        action='store_true',
        help=self._GetHelpText(FlagType.CLEAR))

  @property
  def update_arg(self):
    """Flag that updates value if part of existing field."""
    return None

  @property
  def remove_arg(self):
    """Flag that removes value if part of existing field."""
    return None

  def Generate(self):
    """Returns ArgumentGroup with all flags specified in generator.

    ArgumentGroup is returned where the set flag is mutually exclusive with
    the rest of the update flags. In addition, remove and clear flags are
    mutually exclusive. The following combinations are allowed

    # sets the foo value to value1,value2
    {command} --foo=value1,value2

    # adds values value3
    {command} --add-foo=value3

    # clears values and sets foo to value4,value5
    {command} --add-foo=value4,value5 --clear

    # removes value4 and adds value6
    {command} --add-foo=value6 --remove-foo=value4

    # removes value6 and then re-adds it
    {command} --add-foo=value6 --remove-foo=value6

    Returns:
      base.ArgumentGroup, argument group containing flags
    """
    base_group = base.ArgumentGroup(
        mutex=True,
        required=False,
        hidden=self.is_hidden,
        help='Update {}.'.format(self.arg_name))
    if FlagType.SET in self.flags_to_generate and self.set_arg:
      base_group.AddArgument(self.set_arg)

    update_group = base.ArgumentGroup(required=False)
    if FlagType.UPDATE in self.flags_to_generate and self.update_arg:
      base_group.AddArgument(self.update_arg)

    clear_group = base.ArgumentGroup(
        mutex=True, required=False)
    if FlagType.CLEAR in self.flags_to_generate and self.clear_arg:
      clear_group.AddArgument(self.clear_arg)
    if FlagType.REMOVE in self.flags_to_generate and self.remove_arg:
      clear_group.AddArgument(self.remove_arg)

    if clear_group.arguments:
      update_group.AddArgument(clear_group)
    if update_group.arguments:
      base_group.AddArgument(update_group)

    return base_group

  def _ConvertValue(self, value):
    return arg_utils.ConvertValue(
        self.field, value, repeated=self.repeated, processor=self.processor,
        choices=util.Choice.ToChoiceMap(self.choices))

  def _GetValue(self, namespace, arg, flag_type):
    """Retrieves namespace value associated with flag.

    Args:
      namespace: The parsed command line argument namespace.
      arg: base.Argument, used to get namespace value
      flag_type: Flag_Type, type of the flag

    Returns:
      value parsed from namespace
    """
    if arg is None:
      return None
    flag_name = arg.name
    if flag_name.startswith('--'):
      flag_name = flag_name[2:]

    underscored_name = flag_name.replace('-', '_')
    value = getattr(namespace, underscored_name, None)
    if flag_type in self._flags_to_process:
      return self._ConvertValue(value)
    return value

  def _ParseFromNamespace(self, namespace):
    """Parses all update flags from namespace.

    Args:
      namespace: The parsed command line argument namespace.

    Returns:
      {FlagType: Any}, dictionary of value parsed from each flag type
    """
    return {
        FlagType.SET: self._GetValue(namespace, self.set_arg, FlagType.SET),
        FlagType.CLEAR: self._GetValue(namespace,
                                       self.clear_arg,
                                       FlagType.CLEAR),
        FlagType.REMOVE: self._GetValue(namespace,
                                        self.remove_arg,
                                        FlagType.REMOVE),
        FlagType.UPDATE: self._GetValue(namespace,
                                        self.update_arg,
                                        FlagType.UPDATE)
    }

  def _GetExistingValue(self, existing_message):
    """Retrieves existing field from message."""
    if existing_message:
      existing_value = arg_utils.GetFieldValueFromMessage(
          existing_message, self.api_field)
    else:
      existing_value = None

    if isinstance(existing_value, list):
      existing_value = existing_value.copy()
    return existing_value

  def _ApplySetFlag(self, output, set_val):
    """Updates result to new value."""
    if set_val:
      return set_val
    return output

  def _ApplyClearFlag(self, output, unused_clear_flag):
    """Clears existing value (No-op: implementation in subclass)."""
    return output

  def _ApplyRemoveFlag(self, output, unused_remove_val):
    """Removes existing value (No-op: implementation in subclass)."""
    return output

  def _ApplyUpdateFlag(self, output, unused_update_val):
    """Updates existing value (No-op: implementation in subclass)."""
    return output

  def Parse(self, namespace, existing_message):
    """Parses update flags from namespace and returns updated message field.

    Args:
      namespace: The parsed command line argument namespace.
      existing_message: Apitools message that exists for given resource.

    Returns:
      Modified existing apitools message field.
    """
    result = self._GetExistingValue(existing_message)
    new_values = self._ParseFromNamespace(namespace)

    # Whether or not the flags are mutually exclusive are determined by the
    # ArgumentGroup generated. We do not want to duplicate the mutex logic
    # so instead we consistently apply all flags in same order.

    # Remove values
    result = self._ApplyClearFlag(result, new_values[FlagType.CLEAR])
    result = self._ApplyRemoveFlag(result, new_values[FlagType.REMOVE])

    # Add values
    result = self._ApplySetFlag(result, new_values[FlagType.SET])
    result = self._ApplyUpdateFlag(result, new_values[FlagType.UPDATE])

    return result


class UpdateDefaultArgumentGenerator(UpdateArgumentGenerator):
  """Update flag generator for simple values."""

  @property
  def _help_text(self):
    return {
        FlagType.SET: 'Set {} to new value.'.format(self.arg_name),
        FlagType.CLEAR: 'Clear {} value and set to None.'.format(self.arg_name)
    }

  @property
  def _flags_to_process(self):
    """Set of flag types that need to be converted."""
    return {FlagType.SET}

  def _ApplyClearFlag(self, output, clear_flag):
    if clear_flag:
      return None
    return output


class UpdateListArgumentGenerator(UpdateArgumentGenerator):
  """Update flag generator for list."""

  @property
  def _help_text(self):
    return {
        FlagType.SET: self.help_text,
        FlagType.CLEAR: 'Set to an empty list',
        FlagType.REMOVE: 'Remove element in list',
        FlagType.UPDATE: 'Update element in list or add another element if '
                         'not found.'
    }

  @property
  def _flags_to_process(self):
    """Set of flag types that need to be converted."""
    return {FlagType.SET, FlagType.REMOVE, FlagType.UPDATE}

  @property
  def update_arg(self):
    return base.Argument(
        '--add-{}'.format(self.arg_name),
        action=self.action,
        type=self.flag_type,
        help=self._GetHelpText(FlagType.UPDATE))

  @property
  def remove_arg(self):
    return base.Argument(
        '--remove-{}'.format(self.arg_name),
        action=self.action,
        type=self.flag_type,
        help=self._GetHelpText(FlagType.REMOVE))

  def _ApplyClearFlag(self, output, clear_flag):
    if clear_flag:
      return []
    return output

  def _ApplyRemoveFlag(self, output, remove_val):
    if remove_val:
      return [x for x in output if x not in remove_val]
    return output

  def _ApplyUpdateFlag(self, output, update_val):
    if update_val:
      return output + [x for x in update_val if x not in output]
    return output


class UpdateMapArgumentGenerator(UpdateArgumentGenerator):
  """Update flag generator for key-value pairs ie proto map fields."""

  @property
  def _is_list_field(self):
    return self.field.name == arg_utils.ADDITIONAL_PROPS

  @property
  def _help_text(self):
    return {
        FlagType.SET: self.help_text,
        FlagType.CLEAR: 'Clear to an empty map',
        FlagType.REMOVE: 'Remove element at key',
        FlagType.UPDATE: 'Update element in list or add another element if '
                         'not found.'
    }

  @property
  def _flags_to_process(self):
    """Set of flag types that need to be converted."""
    return {FlagType.SET, FlagType.UPDATE}

  @property
  def update_arg(self):
    return base.Argument(
        '--update-{}'.format(self.arg_name),
        type=self.flag_type,
        action=self.action,
        help=self._GetHelpText(FlagType.UPDATE))

  @property
  def remove_arg(self):
    if self._is_list_field:
      field = self.field
    else:
      field = arg_utils.GetFieldFromMessage(
          self.field.type, arg_utils.ADDITIONAL_PROPS)

    key_field = arg_utils.GetFieldFromMessage(field.type, 'key')
    key_type = key_field.type or arg_utils.TYPES.get(key_field.variant)
    key_list = arg_parsers.ArgList(element_type=key_type)

    return base.Argument(
        '--remove-{}'.format(self.arg_name),
        type=key_list,
        action='store',
        help=self._GetHelpText(FlagType.REMOVE))

  def _WrapOutput(self, output_list):
    """Wraps field AdditionalProperties in apitools message if needed.

    Args:
      output_list: list of apitools AdditionalProperties messages.

    Returns:
      apitools message instance.
    """
    if self._is_list_field:
      return output_list
    message = self.field.type()
    arg_utils.SetFieldInMessage(
        message, arg_utils.ADDITIONAL_PROPS, output_list)
    return message

  def _GetPropsFieldValue(self, field):
    """Retrieves AdditionalProperties field value.

    Args:
      field: apitools instance that contains AdditionalProperties field

    Returns:
      list of apitools AdditionalProperties messages.
    """
    if not field:
      return []
    if self._is_list_field:
      return field
    return arg_utils.GetFieldValueFromMessage(
        field, arg_utils.ADDITIONAL_PROPS)

  def _ApplyClearFlag(self, output, clear_flag):
    if clear_flag:
      return self._WrapOutput([])
    return output

  def _ApplyUpdateFlag(self, output, update_val):
    if update_val:
      output_list = self._GetPropsFieldValue(output)
      update_val_list = self._GetPropsFieldValue(update_val)
      update_key_set = set([x.key for x in update_val_list])
      deduped_list = [x for x in output_list if x.key not in update_key_set]
      return self._WrapOutput(deduped_list + update_val_list)
    return output

  def _ApplyRemoveFlag(self, output, remove_val):
    if remove_val:
      output_list = self._GetPropsFieldValue(output)
      remove_val_set = set(remove_val)
      return self._WrapOutput(
          [x for x in output_list if x.key not in remove_val_set])
    return output
