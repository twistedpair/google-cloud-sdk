# Copyright 2013 Google Inc. All Rights Reserved.
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

"""A module that provides parsing utilities for argparse.

For details of how argparse argument pasers work, see:

  http://docs.python.org/dev/library/argparse.html#type

Example usage:

  import argparse
  import arg_parsers

  parser = argparse.ArgumentParser()

  parser.add_argument(
      '--metadata',
      type=arg_parsers.ArgDict(),
      action=arg_parser.FloatingListValuesCatcher())
  parser.add_argument(
      '--delay',
      default='5s',
      type=arg_parsers.Duration(lower_bound='1s', upper_bound='10s')
  parser.add_argument(
      '--disk-size',
      default='10GB',
      type=arg_parsers.BinarySize(lower_bound='1GB', upper_bound='10TB')

  res = parser.parse_args(
      '--names --metadata x=y,a=b,c=d --delay 1s --disk-size 10gb'.split())

  assert res.metadata == {'a': 'b', 'c': 'd', 'x': 'y'}
  assert res.delay == 1
  assert res.disk_size == 10737418240

"""

import argparse
import copy
import datetime
import re
import sys


__all__ = ['Duration', 'BinarySize']


class Error(Exception):
  """Exceptions that are defined by this module."""


class ArgumentTypeError(Error, argparse.ArgumentTypeError):
  """Exceptions for parsers that are used as argparse types."""


class ArgumentParsingError(Error, argparse.ArgumentError):
  """Raised when there is a problem with user input.

  argparse.ArgumentError takes both the action and a message as constructor
  parameters.
  """


def _GenerateErrorMessage(error, user_input=None, error_idx=None):
  """Constructs an error message for an exception.

  Args:
    error: str, The error message that should be displayed. This
      message should not end with any punctuation--the full error
      message is constructed by appending more information to error.
    user_input: str, The user input that caused the error.
    error_idx: int, The index at which the error occurred. If None,
      the index will not be printed in the error message.

  Returns:
    str: The message to use for the exception.
  """
  if user_input is None:
    return error
  elif not user_input:  # Is input empty?
    return error + '; received empty string'
  elif error_idx is None:
    return error + '; received: ' + user_input
  return ('{error_message} at index {error_idx}: {user_input}'
          .format(error_message=error, user_input=user_input,
                  error_idx=error_idx))


_VALUE_PATTERN = r"""
    ^                       # Beginning of input marker.
    (?P<amount>\d+)         # Amount.
    ((?P<unit>[a-zA-Z]+))?  # Optional unit.
    $                       # End of input marker.
"""

_RANGE_PATTERN = r'^(?P<start>[0-9]+)(-(?P<end>[0-9]+))?$'

_SECOND = 1
_MINUTE = 60 * _SECOND
_HOUR = 60 * _MINUTE
_DAY = 24 * _HOUR

# The units are adopted from sleep(1):
#   http://linux.die.net/man/1/sleep
_DURATION_SCALES = {
    's': _SECOND,
    'm': _MINUTE,
    'h': _HOUR,
    'd': _DAY,
}

_BINARY_SIZE_SCALES = {
    'B': 1,
    'KB': 1 << 10,
    'MB': 1 << 20,
    'GB': 1 << 30,
    'TB': 1 << 40,
    'PB': 1 << 50,
    'KiB': 1 << 10,
    'MiB': 1 << 20,
    'GiB': 1 << 30,
    'TiB': 1 << 40,
    'PiB': 1 << 50,
}


def GetMultiCompleter(individual_completer):
  """Create a completer to handle completion for comma separated lists.

  Args:
    individual_completer: A function that completes an individual element.

  Returns:
    A function that completes the last element of the list.
  """
  def MultiCompleter(prefix, parsed_args, **kwargs):
    start = ''
    lst = prefix.rsplit(',', 1)
    if len(lst) > 1:
      start = lst[0] + ','
      prefix = lst[1]
    matches = individual_completer(prefix, parsed_args, **kwargs)
    return [start+match for match in matches]
  return MultiCompleter


def _ValueParser(scales, default_unit, lower_bound=None, upper_bound=None,
                 strict_case=True, suggested_binary_size_scales=None):
  """A helper that returns a function that can parse values with units.

  Casing for all units matters.

  Args:
    scales: {str: int}, A dictionary mapping units to their magnitudes in
      relation to the lowest magnitude unit in the dict.
    default_unit: str, The default unit to use if the user's input is
      missing unit.
    lower_bound: str, An inclusive lower bound.
    upper_bound: str, An inclusive upper bound.
    strict_case: bool, whether to be strict on case-checking
    suggested_binary_size_scales: list, A list of strings with units that will
                                    be recommended to user.

  Returns:
    A function that can parse values.
  """

  def UnitsByMagnitude(suggested_binary_size_scales=None):
    """Returns a list of the units in scales sorted by magnitude."""
    scale_items = sorted(scales.iteritems(), key=lambda value: value[1])
    if suggested_binary_size_scales is None:
      return [key for key, _ in scale_items]
    return [key for key, _ in scale_items
            if key in suggested_binary_size_scales]

  def Parse(value):
    """Parses value that can contain a unit."""
    match = re.match(_VALUE_PATTERN, value, re.VERBOSE)
    if not match:
      raise ArgumentTypeError(_GenerateErrorMessage(
          'given value must be of the form INTEGER[UNIT] where units '
          'can be one of {0}'
          .format(', '.join(UnitsByMagnitude(suggested_binary_size_scales))),
          user_input=value))

    amount = int(match.group('amount'))
    unit = match.group('unit')
    if strict_case:
      unit_case = unit
      default_unit_case = default_unit
      scales_case = scales
    else:
      unit_case = unit and unit.upper()
      default_unit_case = default_unit.upper()
      scales_case = dict([(k.upper(), v) for k, v in scales.items()])

    if unit_case is None:
      return amount * scales_case[default_unit_case]
    elif unit_case in scales_case:
      return amount * scales_case[unit_case]
    else:
      raise ArgumentTypeError(_GenerateErrorMessage(
          'unit must be one of {0}'.format(', '.join(UnitsByMagnitude())),
          user_input=unit))

  if lower_bound is None:
    parsed_lower_bound = None
  else:
    parsed_lower_bound = Parse(lower_bound)

  if upper_bound is None:
    parsed_upper_bound = None
  else:
    parsed_upper_bound = Parse(upper_bound)

  def ParseWithBoundsChecking(value):
    """Same as Parse except bound checking is performed."""
    if value is None:
      return None
    else:
      parsed_value = Parse(value)
      if parsed_lower_bound is not None and parsed_value < parsed_lower_bound:
        raise ArgumentTypeError(_GenerateErrorMessage(
            'value must be greater than or equal to {0}'.format(lower_bound),
            user_input=value))
      elif parsed_upper_bound is not None and parsed_value > parsed_upper_bound:
        raise ArgumentTypeError(_GenerateErrorMessage(
            'value must be less than or equal to {0}'.format(upper_bound),
            user_input=value))
      else:
        return parsed_value

  return ParseWithBoundsChecking


def Duration(lower_bound=None, upper_bound=None):
  """Returns a function that can parse time durations.

  Input to the parsing function must be a string of the form:

    INTEGER[UNIT]

  The integer must be non-negative. Valid units are "s", "m", "h", and
  "d" for seconds, seconds, minutes, hours, and days,
  respectively. The casing of the units matters.

  If the unit is omitted, seconds is assumed.

  The result is parsed in seconds. For example:

    parser = Duration()
    assert parser('10s') == 10

  Args:
    lower_bound: str, An inclusive lower bound for values.
    upper_bound: str, An inclusive upper bound for values.

  Raises:
    ArgumentTypeError: If either the lower_bound or upper_bound
      cannot be parsed. The returned function will also raise this
      error if it cannot parse its input. This exception is also
      raised if the returned function receives an out-of-bounds
      input.

  Returns:
    A function that accepts a single time duration as input to be
      parsed.
  """
  return _ValueParser(_DURATION_SCALES, default_unit='s',
                      lower_bound=lower_bound, upper_bound=upper_bound)


def BinarySize(lower_bound=None, upper_bound=None,
               suggested_binary_size_scales=None):
  """Returns a function that can parse binary sizes.

  Binary sizes are defined as base-2 values representing number of
  bytes.

  Input to the parsing function must be a string of the form:

    INTEGER[UNIT]

  The integer must be non-negative. Valid units are "B", "KB", "MB",
  "GB", "TB", "KiB", "MiB", "GiB", "TiB", "PiB".  If the unit is
  omitted, GB is assumed.

  The result is parsed in bytes. For example:

    parser = BinarySize()
    assert parser('10GB') == 1073741824

  Args:
    lower_bound: str, An inclusive lower bound for values.
    upper_bound: str, An inclusive upper bound for values.
    suggested_binary_size_scales: list, A list of strings with units that will
                                    be recommended to user.

  Raises:
    ArgumentTypeError: If either the lower_bound or upper_bound
      cannot be parsed. The returned function will also raise this
      error if it cannot parse its input. This exception is also
      raised if the returned function receives an out-of-bounds
      input.

  Returns:
    A function that accepts a single binary size as input to be
      parsed.
  """
  return _ValueParser(
      _BINARY_SIZE_SCALES, default_unit='GB',
      lower_bound=lower_bound, upper_bound=upper_bound,
      strict_case=False,
      suggested_binary_size_scales=suggested_binary_size_scales)


_KV_PAIR_DELIMITER = '='


class Range(object):
  """Range of integer values."""

  def __init__(self, start, end):
    self.start = start
    self.end = end

  @staticmethod
  def Parse(string_value):
    """Creates Range object out of given string value."""
    match = re.match(_RANGE_PATTERN, string_value)
    if not match:
      raise ArgumentTypeError('Expected a non-negative integer value or a '
                              'range of such values instead of "{0}"'
                              .format(string_value))
    start = int(match.group('start'))
    end = match.group('end')
    if end is None:
      end = start
    else:
      end = int(end)
    if end < start:
      raise ArgumentTypeError('Expected range start {0} smaller or equal to '
                              'range end {1} in "{2}"'.format(
                                  start, end, string_value))
    return Range(start, end)

  def Combine(self, other):
    """Combines two overlapping or adjacent ranges, raises otherwise."""
    if self.end + 1 < other.start or self.start > other.end + 1:
      raise Error('Cannot combine non-overlapping or non-adjacent ranges '
                  '{0} and {1}'.format(self, other))
    return Range(min(self.start, other.start), max(self.end, other.end))

  def __eq__(self, other):
    if isinstance(other, Range):
      return self.start == other.start and self.end == other.end
    return False

  def __lt__(self, other):
    if self.start == other.start:
      return self.end < other.end
    return self.start < other.start

  def __str__(self):
    if self.start == self.end:
      return str(self.start)
    return '{0}-{1}'.format(self.start, self.end)


class HostPort(object):
  """A class for holding host and port information."""

  IPV4_OR_HOST_PATTERN = r'^(?P<address>[\w\d\.-]+)?(:|:(?P<port>[\d]+))?$'
  # includes hostnames
  IPV6_PATTERN = r'^(\[(?P<address>[\w\d:]+)\])(:|:(?P<port>[\d]+))?$'

  def __init__(self, host, port):
    self.host = host
    self.port = port

  @staticmethod
  def Parse(s, ipv6_enabled=False):
    """Parse the given string into a HostPort object.

    This can be used as an argparse type.

    Args:
      s: str, The string to parse. If ipv6_enabled and host is an IPv6 address,
      it should be placed in square brackets: e.g.
        [2001:db8:0:0:0:ff00:42:8329]
        or
        [2001:db8:0:0:0:ff00:42:8329]:8080
      ipv6_enabled: boolean, If True then accept IPv6 addresses.

    Raises:
      ArgumentTypeError: If the string is not valid.

    Returns:
      HostPort, The parsed object.
    """
    if not s:
      return HostPort(None, None)

    match = re.match(HostPort.IPV4_OR_HOST_PATTERN, s, re.UNICODE)
    if ipv6_enabled and not match:
      match = re.match(HostPort.IPV6_PATTERN, s, re.UNICODE)
      if not match:
        raise ArgumentTypeError(_GenerateErrorMessage(
            'Failed to parse host and port. Expected format \n\n'
            '  IPv4_ADDRESS_OR_HOSTNAME:PORT\n\n'
            'or\n\n'
            '  [IPv6_ADDRESS]:PORT\n\n'
            '(where :PORT is optional).',
            user_input=s))
    elif not match:
      raise ArgumentTypeError(_GenerateErrorMessage(
          'Failed to parse host and port. Expected format \n\n'
          '  IPv4_ADDRESS_OR_HOSTNAME:PORT\n\n'
          '(where :PORT is optional).',
          user_input=s))
    return HostPort(match.group('address'), match.group('port'))


class Day(object):
  """A class for parsing a datetime object for a specific day."""

  @staticmethod
  def Parse(s):
    if not s:
      return None
    try:
      return datetime.datetime.strptime(s, '%Y-%m-%d').date()
    except ValueError:
      raise ArgumentTypeError(
          _GenerateErrorMessage(
              "Failed to parse date. Value should be in the form 'YYYY-MM-DD",
              user_input=s))


class Datetime(object):
  """A class for parsing a datetime object in UTC timezone."""

  @staticmethod
  def Parse(s):
    """Parses a string value into a Datetime object."""
    if not s:
      return None
    accepted_formats = ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f',
                        '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S.%fZ')
    # TODO(user): Add timezone support.
    for date_format in accepted_formats:
      try:
        return datetime.datetime.strptime(s, date_format)
      except ValueError:
        pass
    raise ArgumentTypeError(
        _GenerateErrorMessage(
            'Failed to parse date. Value should be in ISO or RFC3339 format',
            user_input=s))


def _BoundedType(type_builder, type_description,
                 lower_bound=None, upper_bound=None, unlimited=False):
  """Returns a function that can parse given type within some bound.

  Args:
    type_builder: A callable for building the requested type from the value
        string.
    type_description: str, Description of the requested type (for verbose
        messages).
    lower_bound: of type compatible with type_builder,
        The value must be >= lower_bound.
    upper_bound: of type compatible with type_builder,
        The value must be <= upper_bound.
    unlimited: bool, If True then a value of 'unlimited' means no limit.

  Returns:
    A function that can parse given type within some bound.
  """

  def Parse(value):
    """Parses value as a type constructed by type_builder.

    Args:
      value: str, Value to be converted to the requested type.

    Raises:
      ArgumentTypeError: If the provided value is out of bounds or unparsable.

    Returns:
      Value converted to the requested type.
    """
    if unlimited and value == 'unlimited':
      return None

    try:
      v = type_builder(value)
    except ValueError:
      raise ArgumentTypeError(
          _GenerateErrorMessage('Value must be {0}'.format(type_description),
                                user_input=value))

    if lower_bound is not None and v < lower_bound:
      raise ArgumentTypeError(
          _GenerateErrorMessage(
              'Value must be greater than or equal to {0}'.format(lower_bound),
              user_input=value))

    if upper_bound is not None and upper_bound < v:
      raise ArgumentTypeError(
          _GenerateErrorMessage(
              'Value must be less than or equal to {0}'.format(upper_bound),
              user_input=value))

    return v

  return Parse


def BoundedInt(*args, **kwargs):
  return _BoundedType(int, 'an integer', *args, **kwargs)


def BoundedFloat(*args, **kwargs):
  return _BoundedType(float, 'a floating point number', *args, **kwargs)


def _TokenizeQuotedList(arg_value, delim=','):
  """Tokenize an argument into a list.

  Args:
    arg_value: str, The raw argument.
    delim: str, The delimiter on which to split the argument string.

  Returns:
    [str], The tokenized list.
  """
  if arg_value:
    if not arg_value.endswith(delim):
      arg_value += delim
    return arg_value.split(delim)[:-1]
  return []


class ArgType(object):
  """Base class for arg types."""


class ArgList(ArgType):
  """Interpret an argument value as a list.

  Intended to be used as the type= for a flag argument. Splits the string on
  commas or another delimiter and returns a list.

  By default, splits on commas:
      'a,b,c' -> ['a', 'b', 'c']
  There is an available syntax for using an alternate delimiter:
      '^:^a,b:c' -> ['a,b', 'c']
      '^::^a:b::c' -> ['a:b', 'c']
      '^,^^a^,b,c' -> ['^a^', ',b', 'c']
  """

  DEFAULT_DELIM_CHAR = ','
  ALT_DELIM_CHAR = '^'

  def __init__(self, element_type=None, min_length=0, max_length=None,
               choices=None):
    """Initialize an ArgList.

    Args:
      element_type: (str)->str, A function to apply to each of the list items.
      min_length: int, The minimum size of the list.
      max_length: int, The maximum size of the list.
      choices: [element_type], a list of valid possibilities for elements. If
          None, then no constraints are imposed.

    Returns:
      (str)->[str], A function to parse the list of values in the argument.

    Raises:
      ArgumentTypeError: If the list is malformed.
    """
    self.element_type = element_type

    if choices:
      def ChoiceType(raw_value):
        if element_type:
          typed_value = element_type(raw_value)
        else:
          typed_value = raw_value
        if typed_value not in choices:
          raise ArgumentTypeError('{value} must be one of [{choices}]'.format(
              value=typed_value, choices=', '.join(
                  [str(choice) for choice in choices])))
        return typed_value
      self.element_type = ChoiceType

    self.min_length = min_length
    self.max_length = max_length

  def __call__(self, arg_value):  # pylint:disable=missing-docstring

    delim = self.DEFAULT_DELIM_CHAR
    if (arg_value.startswith(self.ALT_DELIM_CHAR) and
        self.ALT_DELIM_CHAR in arg_value[1:]):
      delim, arg_value = arg_value[1:].split(self.ALT_DELIM_CHAR, 1)
      if not delim:
        raise ArgumentTypeError(
            'Invalid delimiter. Please see `gcloud topic escaping` for '
            'information on escaping list or dictionary flag values.')
    arg_list = _TokenizeQuotedList(arg_value, delim=delim)

    # TODO(user): These exceptions won't present well to the user.
    if len(arg_list) < self.min_length:
      raise ArgumentTypeError('not enough args')
    if self.max_length is not None and len(arg_list) > self.max_length:
      raise ArgumentTypeError('too many args')

    if self.element_type:
      arg_list = [self.element_type(arg) for arg in arg_list]

    return arg_list


class ArgDict(ArgList):
  """Interpret an argument value as a dict.

  Intended to be used as the type= for a flag argument. Splits the string on
  commas to get a list, and then splits the items on equals to get a set of
  key-value pairs to get a dict.
  """

  def __init__(self, value_type=None, spec=None, min_length=0, max_length=None):
    """Initialize an ArgDict.

    Args:
      value_type: (str)->str, A function to apply to each of the dict values.
      spec: {str: (str)->str}, A mapping of expected keys to functions.
        The functions are applied to the values. If None, an arbitrary
        set of keys will be accepted. If not None, it is an error for the
        user to supply a key that is not in the spec.
      min_length: int, The minimum number of keys in the dict.
      max_length: int, The maximum number of keys in the dict.

    Returns:
      (str)->{str:str}, A function to parse the dict in the argument.

    Raises:
      ArgumentTypeError: If the list is malformed.
      ValueError: If both value_type and spec are provided.
    """
    super(ArgDict, self).__init__(min_length=min_length, max_length=max_length)
    if spec and value_type:
      raise ValueError('cannot have both spec and sub_type')
    self.value_type = value_type
    self.spec = spec

  def _ApplySpec(self, key, value):
    if key in self.spec:
      return self.spec[key](value)
    else:
      raise ArgumentTypeError(
          _GenerateErrorMessage(
              'valid keys are {0}'.format(
                  ', '.join(sorted(self.spec.keys()))),
              user_input=key))

  def __call__(self, arg_value):  # pylint:disable=missing-docstring
    arg_list = super(ArgDict, self).__call__(arg_value)

    arg_dict = {}
    for arg in arg_list:
      split_arg = arg.split('=', 1)  # only use the first =
      # TODO(user): These exceptions won't present well to the user.
      if len(split_arg) != 2:
        raise ArgumentTypeError(
            ('Bad syntax for dict arg: {0}. Please see `gcloud topic escaping` '
             'if you would like information on escaping list or dictionary '
             'flag values.').format(repr(arg)))
      key, value = split_arg
      if not key:
        raise ArgumentTypeError('bad key for dict arg: '+repr(arg))
      if self.value_type:
        value = self.value_type(value)
      if self.spec:
        value = self._ApplySpec(key, value)
      arg_dict[key] = value

    return arg_dict


# pylint:disable=protected-access
def FloatingListValuesCatcher(
    action=argparse._StoreAction, switch_value=None):
  """Create an action for catching floating list values.

  Args:
    action: argparse.Action, the superclass of the new action.
    switch_value: obj, If not none, allow users to specify no value for the
        flag. If the flag is given and no value is specified, the switch_value
        will be used instead.

  Returns:
    argparse.Action, an action that will catch list values separated by spaces.
  """

  class FloatingListValuesCatcherAction(action):
    """This is to assist with refactoring argument lists.

    Provides an error for users who type (or have a script) that specifies a
    list with the elements in different arguments. eg.
     $ gcloud sql instances create foo --authorized-networks x y
     usage: gcloud sql instances create  INSTANCE [optional flags]
     ERROR: (gcloud.sql.instances.create) argument --authorized-networks: lists
     are separated by commas, try "--authorized-networks=x,y"

    To do this, with flags that used to (but no longer) have nargs set to take
    multiple values we apply an action designed to catch them by transparently
    setting nargs to '+', and then making sure only 1 value is provided.

    As a caveat, this means that people still cannot put positional arguments
    after the flags. So, this is a temporary mechanism designed to inform users,
    and we'll remove it eventually.
    """

    # TODO(user): remove this.
    _NOLINT = True

    def __init__(self, *args, **kwargs):
      if 'nargs' in kwargs:
        # Make sure nothing weird is happening, first. This action is intended
        # only for use with --flags that have the type as ArgList or ArgDict,
        # and do not set nargs at all.
        raise ValueError(
            'trying to catch floating lists for a misspecified flag list')
      if switch_value is not None:
        kwargs['nargs'] = '*'
      else:
        kwargs['nargs'] = '+'
      super(FloatingListValuesCatcherAction, self).__init__(*args, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
      class ArgShell(object):
        """Class designed to trick argparse into displaying a nice error."""

        def __init__(self, name):
          self.option_strings = [name]

      if not values and switch_value is not None:
        msg = (
            'We noticed that you provided no value for flag [{flag}]. This '
            'behavior is deprecated.\nInstead, please provide an empty string '
            'as the explicit value (try [{flag} \'\']).').format(
                flag=option_string)
        raise argparse.ArgumentError(ArgShell(option_string), msg)

      if len(values) > 1:

        suggestions = []
        if values and isinstance(values[0], dict):
          aggregate_value = {}
          for valdict in values:
            aggregate_value.update(valdict)
            suggestions.extend(
                ['%s=%s' % (k, v) for k, v in valdict.iteritems()])
        if values and isinstance(values[0], list):
          aggregate_value = []
          suggestions.extend(
              [','.join(map(str, vallist)) for vallist in values])
          for vallist in values:
            aggregate_value.extend(vallist)
        extras = suggestions[1:]

        msg = (
            'We noticed that you are using space-separated lists, which are '
            'deprecated. '
            'Please transition to using comma-separated lists instead '
            '(try "{flag} {values}"). '
            'If you intend to use [{extras}] as positional arguments, put the '
            'flags at the end.').format(
                flag=option_string,
                values=','.join(suggestions),
                extras=', '.join(extras))

        raise argparse.ArgumentError(ArgShell(option_string), msg)
      else:
        super(FloatingListValuesCatcherAction, self).__call__(
            parser, namespace, values[0], option_string=option_string)

  return FloatingListValuesCatcherAction


class UpdateAction(argparse.Action):
  r"""Create a single dict value from delimited or repeated flags.

  This class is intended to be a more flexible version of
  argparse._AppendAction.

  For example, with the following flag definition:

      parser.add_argument(
        '--inputs',
        type=arg_parsers.ArgDict(),
        action=arg_parsers.FloatingListValuesCatcher(
            arg_parsers._AppendAction),

  a caller can specify on the command line flags such as:

    --inputs k1=v1,k2=v2

  and the result will be a list of one dict:

    [{ 'k1': 'v1', 'k2': 'v2' }]

  Specifying two separate command line flags such as:

    --inputs k1=v1 \
    --inputs k2=v2

  will produce a list of dicts:

    [{ 'k1': 'v1'}, 'k2': 'v2' }]

  The UpdateAction class allows for both of the above user inputs to result
  in the same: a single dictionary:

    { 'k1': 'v1', 'k2': 'v2' }

  This gives end-users a lot more flexibility in constructing their command
  lines, especially when scripting calls.

  Note that this class will raise an exception if a key value is specified
  more than once. To allow for a key value to be specified multiple times,
  use UpdateActionWithAppend.
  """

  def OnDuplicateKeyRaiseError(self, key, existing_value=None, new_value=None):
    if existing_value is None:
      user_input = None
    else:
      user_input = ', '.join([existing_value, new_value])
    raise argparse.ArgumentError(self, _GenerateErrorMessage(
        '"{0}" cannot be specified multiple times'.format(key),
        user_input=user_input))

  def __init__(self,
               option_strings,
               dest,
               nargs=None,
               const=None,
               default=None,
               type=None,  # pylint:disable=redefined-builtin
               choices=None,
               required=False,
               help=None,  # pylint:disable=redefined-builtin
               metavar=None,
               onduplicatekey_handler=OnDuplicateKeyRaiseError):
    if nargs == 0:
      raise ValueError('nargs for append actions must be > 0; if arg '
                       'strings are not supplying the value to append, '
                       'the append const action may be more appropriate')
    if const is not None and nargs != argparse.OPTIONAL:
      raise ValueError('nargs must be %r to supply const' % argparse.OPTIONAL)
    super(UpdateAction, self).__init__(
        option_strings=option_strings,
        dest=dest,
        nargs=nargs,
        const=const,
        default=default,
        type=type,
        choices=choices,
        required=required,
        help=help,
        metavar=metavar)
    self.onduplicatekey_handler = onduplicatekey_handler

  def __call__(self, parser, namespace, values, option_string=None):

    if isinstance(values, dict):
      # Get the existing arg value (if any)
      items = copy.copy(argparse._ensure_value(namespace, self.dest, {}))
      # Merge the new key/value pair(s) in
      for k, v in values.iteritems():
        if k in items:
          v = self.onduplicatekey_handler(self, k, items[k], v)
        items[k] = v
    else:
      # Get the existing arg value (if any)
      items = copy.copy(argparse._ensure_value(namespace, self.dest, []))
      # Merge the new key/value pair(s) in
      for k in values:
        if k in items:
          self.onduplicatekey_handler(self, k)
        else:
          items.append(k)

    # Saved the merged dictionary
    setattr(namespace, self.dest, items)


class UpdateActionWithAppend(UpdateAction):
  """Create a single dict value from delimited or repeated flags.

  This class provides a variant of UpdateAction, which allows for users to
  append, rather than reject, duplicate key values. For example, the user
  can specify:

    --inputs k1=v1a --inputs k1=v1b --inputs k2=v2

  and the result will be:

     { 'k1': ['v1a', 'v1b'], 'k2': 'v2' }
  """

  def OnDuplicateKeyAppend(self, key, existing_value=None, new_value=None):
    if existing_value is None:
      return key
    elif isinstance(existing_value, list):
      return existing_value + [new_value]
    else:
      return [existing_value, new_value]

  def __init__(self,
               option_strings,
               dest,
               nargs=None,
               const=None,
               default=None,
               type=None,  # pylint:disable=redefined-builtin
               choices=None,
               required=False,
               help=None,  # pylint:disable=redefined-builtin
               metavar=None,
               onduplicatekey_handler=OnDuplicateKeyAppend):
    super(UpdateActionWithAppend, self).__init__(
        option_strings=option_strings,
        dest=dest,
        nargs=nargs,
        const=const,
        default=default,
        type=type,
        choices=choices,
        required=required,
        help=help,
        metavar=metavar,
        onduplicatekey_handler=onduplicatekey_handler)


class BufferedFileInput(object):
  """Creates an argparse type that reads and buffers file or stdin contents.

  This is similar to argparse.FileType, but unlike FileType it does not leave
  a dangling file handle open. The argument stored in the argparse Namespace
  is the file's contents.

  Args:
    max_bytes: int, The maximum file size in bytes, or None to specify no
        maximum.
    chunk_size: int, When max_bytes is not None, the buffer size to use when
        reading chunks from the input file.

  Returns:
    A function that accepts a filename, or "-" representing that stdin should be
    used as input.
  """

  def __init__(self, max_bytes=None, chunk_size=16*1024):
    self.max_bytes = max_bytes
    self.chunk_size = chunk_size

  def _ReadFile(self, f):
    # Unbounded
    if self.max_bytes is None:
      return f.read()
    else:
      contents = ''
      while True:
        chunk = f.read(self.chunk_size)

        # Check for EOF
        if not chunk:
          return contents
        # Fail if the file is too large.
        if len(contents) + len(chunk) > self.max_bytes:
          if hasattr(f, 'name'):
            raise ArgumentTypeError("File '{0}' is too large.".format(f.name))
          else:
            raise ArgumentTypeError('File is too large.')

        contents += chunk

  def __call__(self, name):
    """Return the contents of the file with the specified name.

    If name is "-", stdin is read until EOF. Otherwise, the named file is read.
    If max_bytes is provided when calling BufferedFileInput, this function will
    raise an ArgumentTypeError if the specified file is too large.

    Args:
      name: str, The file name, or '-' to indicate stdin.

    Returns:
      The contents of the file.

    Raises:
      ArgumentTypeError: If the file cannot be read or is too large.
    """
    # Handle stdin
    if name == '-':
      return self._ReadFile(sys.stdin)

    try:
      with open(name, 'r') as f:
        return self._ReadFile(f)
    except (IOError, OSError) as e:
      raise ArgumentTypeError(
          "Can't open '{0}': {1}".format(name, e))
