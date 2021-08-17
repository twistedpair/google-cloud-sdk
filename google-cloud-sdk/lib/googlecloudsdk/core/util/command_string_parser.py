# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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

"""A module that provides parsing utilities for each command example."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections


class CommandStringParser(object):
  """Object which builds and returns all metadata about string and flags.

  Attributes:
    command_node: calliope._CommandCommon, The command object that has access
    to argparse.
    command_parser: The argparse object for command_node.
    example_string: The most recently parsed example command string.
    example_metadata: The metadata gotten from example_string.
  """

  def __init__(self, command_node):
    self.command_node = command_node
    self.command_parser = self.command_node._parser

  def parse(self, example_command_string):
    """Gets relevant metadata from an example command string.

    Args:
      example_command_string: The example command string to be parsed.

    Returns:
      An ExampleCommandMetadata object containing the relevant metadata or None
      if there was a parsing error.
    """
    self.example_string = example_command_string
    self.example_metadata = ExampleCommandMetadata()

    parse_input = self.get_parse_args(example_command_string)
    if not parse_input:
      return

    metadata = self.command_parser.parse_args(parse_input, raise_error=True)

    filtered = metadata.GetSpecifiedArgsDict()
    prev_stop = 0  # Keeps track of where the previous argument stopped

    for key, value in filtered.items():
      tmp_value = getattr(metadata, key, None)
      if isinstance(tmp_value, list):
        prev_stop = self.parse_list(tmp_value, key, value, prev_stop)

      elif isinstance(tmp_value, collections.OrderedDict):
        prev_stop = self.parse_dict(tmp_value, key, prev_stop)

      else:
        prev_stop = self.parse_others(tmp_value, key, value, prev_stop)

    return self.example_metadata

  def parse_dict(self, dict_arg, key, prev_stop, count=None):
    """Gets metadata from an example command string for a simple dict-type arg.

    It updates the already existing ExampleCommandMetadata object of the example
    string with the metadata.

    Args:
      dict_arg: The dictionary-type argument to collect metadata about.
      key: The name of the argument's attribute in the example string's
      namespace.
      prev_stop: The index in the example string where the last flag stopped.
      count: Optional. The number of times the flag has been seen in the example
      string.

    Returns:
      The index in the example string where parsing stopped.
    """
    dict_list = list(dict_arg.items())
    first_pair = dict_list[0]
    last_pair = dict_list[-1]
    start_index = self.example_string.index(str(first_pair[0]), prev_stop)
    next_start = self.example_string.find('--', start_index)
    if next_start < prev_stop: next_start = len(self.example_string)
    last_value = str(last_pair[1])
    last_value_start = self.example_string.rfind(last_value, prev_stop,
                                                 next_start)
    stop_index = last_value_start + len(last_value) - 1

    arg_value = self.example_string[start_index:stop_index+1]
    # If count, dict_arg is part of a list and arg's action is append.
    # Otherwise, it's a normal dictionary arg.
    scope = '{key}_{count}'.format(key=key, count=count) if count else key
    arg_metadata = ArgumentMetadata(key, arg_value, scope,
                                    start_index, stop_index)
    self.example_metadata.add_arg_metadata(arg_metadata)
    prev_stop = stop_index + 1

    return prev_stop

  def parse_list(self, list_arg, key, value, prev_stop, count=None):
    """Gets metadata from an example command string for a list-type argument.

    It updates the already existing ExampleCommandMetadata object of the example
    string with the metadata.

    Args:
      list_arg: The list-type argument to collect metadata about.
      key: The name of the argument's attribute in the example string's
      namespace.
      value: The actual input representing the flag/argument in the example
      string (e.g --zone, --shielded-secure-boot).
      prev_stop: The index in the example string where the last flag stopped.
      count: Optional. The number of times the flag has been seen in the example
      string.

    Returns:
      The index in the example string where parsing stopped.
    """
    if isinstance(list_arg[0], collections.OrderedDict):
      prev_stop = self.parse_nested_list(list_arg, key, value, prev_stop)

    elif isinstance(list_arg[0], list):
      prev_stop = self.parse_nested_list(list_arg, key, value, prev_stop)

    else:
      # Assumes list elements are either strings or numbers; excludes booleans.

      start_index = self.example_string.index(str(list_arg[0]), prev_stop)
      next_start = self.example_string.find('--', start_index)
      if next_start < prev_stop or next_start == -1:
        next_start = len(self.example_string)
      last_value = str(list_arg[-1])
      last_value_start = self.example_string.rfind(last_value, prev_stop,
                                                   next_start)
      stop_index = last_value_start + len(last_value) -1
      arg_value = self.example_string[start_index:stop_index+1]
      scope = '{key}_{count}'.format(key=key, count=count) if count else key
      # count implies list_arg is an inner list which implies action is append.
      # no count implies simple list which implies action is update.

      arg_metadata = ArgumentMetadata(key, arg_value, scope, start_index,
                                      stop_index)
      self.example_metadata.add_arg_metadata(arg_metadata)
      prev_stop = stop_index + 1

    return prev_stop

  def parse_nested_list(self, list_arg, key, value, prev_stop):
    """Gets metadata from an example command string for nested list arguments.

    This is a helper function for parse_list().

    It updates the already existing ExampleCommandMetadata object of the example
    string with the metadata.

    Args:
      list_arg: The list-type argument to collect metadata about.
      key: The name of the argument's attribute in the example string's
      namespace.
      value: The actual input representing the flag/argument in the example
      string (e.g --zone, --shielded-secure-boot).
      prev_stop: The index in the example string where the last flag stopped.

    Returns:
      The index in the example string where parsing stopped.
    """
    if isinstance(list_arg[0], collections.OrderedDict):
      flag_count = self.example_string.count(value)

      # Flag specified once in example string and occurs multiple times in
      # namespace implies flag was specified with custom delimiter.
      if flag_count == 1 and len(list_arg) > 1:
        first_dict = list(list_arg[0].items())
        last_dict = list(list_arg[-1].items())
        start = first_dict[0][0]  # first key of first dictionary
        stop = last_dict[-1][1]  # last key of last dictionary

        start_index = self.example_string.index(str(start))
        next_start = self.example_string.find('--', start_index)
        if next_start < prev_stop: next_start = len(self.example_string)
        stop_index = (self.example_string.rfind(str(stop), prev_stop,
                                                next_start) +
                      len(str(stop)) - 1)

        prev_stop = stop_index + 1
        arg_value = self.example_string[start_index:stop_index+1]
        arg_metadata = ArgumentMetadata(key, arg_value, key, start_index,
                                        stop_index)
        self.example_metadata.add_arg_metadata(arg_metadata)

      # Flag specified multiple times in both example string namespace implies
      # flag's action is append.
      else:
        count = 1
        for val in list_arg:
          prev_stop = self.parse_dict(val, key, prev_stop, count)
          count += 1

    # Nested list(list_arg[0] is a list) implies action is append.
    else:

      count = 1
      for val in list_arg:
        prev_stop = self.parse_list(val, key, value, prev_stop, count)
        count += 1

    return prev_stop

  def parse_others(self, other_arg, key, value, prev_stop):
    """Gets metadata from an example string for non list-type/dict-type args.

    It updates the already existing ExampleCommandMetadata object of the example
    string with the metadata.

    Args:
      other_arg: The non list-type and non dict-type argument to collect
      metadata about.
      key: The name of the argument's attribute in the example string's
      namespace.
      value: The actual input representing the flag/argument in the example
      string (e.g --zone, --shielded-secure-boot).
      prev_stop: The index in the example string where the last flag stopped.

    Returns:
      The index in the example string where parsing stopped.
    """
    # Editable range includes quotes and excludes booleans.

    if isinstance(other_arg, bool):
      prev_stop = self.example_string.index(value, prev_stop) + len(value)

    else:
      start_index = self.example_string.find(str(other_arg), prev_stop)
      if start_index == -1:
        #  Enum type
        other_arg = self.get_enum_value(other_arg, prev_stop)

      start_index = self.example_string.index(str(other_arg), prev_stop)
      arg_metadata = ArgumentMetadata(key, other_arg, key, start_index,
                                      start_index + len(str(other_arg)) - 1)

      self.example_metadata.add_arg_metadata(arg_metadata)
      prev_stop = arg_metadata.stop_index + 1

    return prev_stop

  def get_enum_value(self, enum_value, prev_stop):
    """Gets the input value of an enum argument in the example string.

    This is a helper function for parse_others().

    Args:
      enum_value: The namespace value of the argument in question.
      prev_stop: The index in the example string where parsing stopped.

    Returns:
     The actual input in the example string representing the argument's value.
    """
    #  Check for common variations(underscore/hypen; lower/upper)
    possible_versions = [enum_value.lower(), enum_value.upper(),
                         enum_value.replace('-', '_'),
                         enum_value.replace('_', '-')]
    unparsed_string = self.example_string[prev_stop:]
    for version in possible_versions:
      if version in unparsed_string:
        enum_value = version

    if enum_value not in unparsed_string:
      unparsed_string = unparsed_string.strip()
      arg_end = unparsed_string.find(' --')
      # Keep last character if we are at the end of the example.
      arg_list = (unparsed_string[:arg_end].split('=') if arg_end != -1
                  else unparsed_string.split('='))

      enum_value = (' '.join(arg_list[1:]).strip() if len(arg_list) > 2 else
                    arg_list[-1].strip())
      # We'll strip the whitespace so it won't be part of the argument value.

    return enum_value

  def get_parse_args(self, string):
    """Gets a list of arguments in a string.

    (Note: It assumes '$' is not included in the string)

    Args:
      string: The string in question.

    Returns:
      A list of the arguments from the string.
    """
    command_name = self.command_node.name.replace('_', '-')
    args_list = string.split('--')
    command_name_start = args_list[0].find(command_name)

    # Return None if command string is under a different command node.
    if command_name_start == -1:
      return
    # calculation includes the space after the command string.
    command_name_stop = command_name_start + len(command_name)+ 1

    args = []
    positional_args = args_list[0][command_name_stop:].strip()
    if positional_args:
      args.append(positional_args)

    for i in range(1, len(args_list)):
      entire_arg = args_list[i].split('=')
      args.append('--' + entire_arg[0].strip())

      if len(entire_arg) > 1:
        args.append('='.join(entire_arg[1:]).strip())
    return args


class ExampleCommandMetadata(object):
  """Encapsulates metadata about entire example command string.

  Attributes:
    argument_metadatas: A list containing the metadata for each argument in an
    example command string.
  """

  def __init__(self):
    self._argument_metadatas = []

  def add_arg_metadata(self, arg_metadata):
    """Adds an argument's metadata to comprehensive metadata list.

    Args:
      arg_metadata: The argument metadata to be added.
    """
    self._argument_metadatas.append(arg_metadata)

  def get_argument_metadatas(self):
    """Returns the metadata for an entire example command string."""
    return sorted(self._argument_metadatas, key=lambda x: x.stop_index)

  def __eq__(self, other):
    if isinstance(other, ExampleCommandMetadata):
      # sort both first
      our_data = sorted(self._argument_metadatas, key=lambda x: x.stop_index)
      other_data = sorted(other._argument_metadatas, key=lambda x: x.stop_index)

      if len(our_data) != len(other_data):
        return False

      for i in range(len(self._argument_metadatas)):
        if our_data[i] != other_data[i]:
          return False
      return True

    return False

  def __ne__(self, other):
    return self.__eq__(other)

  def __str__(self):
    metadatas = self.get_argument_metadatas()
    result = [str(data) for data in metadatas]
    return '[{result}]'.format(result=',  '.join(result))


class ArgumentMetadata(object):
  """Encapsulates metadata about a single argument.

  Attributes:
    arg_name: The name of the argument.
    arg_value: Value of the argument.
    scope: The scope of the argument.
    start_index: The  index where the argument starts in the command string.
    stop_index: The index where the argument stops in the command string.
  """

  def __init__(self, arg_name, arg_value, scope, start_index, stop_index):
    self.arg_name = arg_name
    self.arg_value = arg_value
    self.scope = scope
    self.start_index = start_index
    self.stop_index = stop_index

  def __str__(self):
    """Returns a human-readable representation of an argument's metadata."""
    return ('ArgumentMetadata(name={name},  value={value},  scope={scope},  '
            'start_index={start},  stop_index='
            '{stop})').format(name=self.arg_name, scope=self.scope,
                              value=self.arg_value, start=self.start_index,
                              stop=self.stop_index)

  def __eq__(self, other):
    if isinstance(other, ArgumentMetadata):
      return (self.arg_name == other.arg_name and
              self.arg_value == other.arg_value and
              self.scope == other.scope and
              self.start_index == other.start_index and
              self.stop_index == other.stop_index)

    return False

  def __ne__(self, other):
    return not self.__eq__(other)
