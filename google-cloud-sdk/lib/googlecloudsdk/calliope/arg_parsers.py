# Copyright 2013 Google Inc. All Rights Reserved.

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

  # will emit a warning about space-separated metadata
  res = parser.parse_args(
      '--names --metadata x=y,a=b c=d --delay 1s --disk-size 10gb'.split())

  assert res.metadata == {'a': 'b', 'c': 'd', 'x': 'y'}
  assert res.delay == 1
  assert res.disk_size == 10737418240

"""

import argparse
import datetime
import re

from googlecloudsdk.core import log

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


def _ValueParser(scales, default_unit, lower_bound=None, upper_bound=None):
  """A helper that returns a function that can parse values with units.

  Casing for all units matters.

  Args:
    scales: {str: int}, A dictionary mapping units to their magnitudes in
      relation to the lowest magnitude unit in the dict.
    default_unit: str, The default unit to use if the user's input is
      missing unit.
    lower_bound: str, An inclusive lower bound.
    upper_bound: str, An inclusive upper bound.

  Returns:
    A function that can parse values.
  """

  def UnitsByMagnitude():
    """Returns a list of the units in scales sorted by magnitude."""
    return [key for key, _
            in sorted(scales.iteritems(), key=lambda value: value[1])]

  def Parse(value):
    """Parses value that can contain a unit."""
    match = re.match(_VALUE_PATTERN, value, re.VERBOSE)
    if not match:
      raise ArgumentTypeError(_GenerateErrorMessage(
          'given value must be of the form INTEGER[UNIT] where units '
          'can be one of {0}'
          .format(', '.join(UnitsByMagnitude())),
          user_input=value))

    amount = int(match.group('amount'))
    unit = match.group('unit')
    if unit is None:
      return amount * scales[default_unit]
    elif unit in scales:
      return amount * scales[unit]
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


def BinarySize(lower_bound=None, upper_bound=None):
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
  return _ValueParser(_BINARY_SIZE_SCALES, default_unit='GB',
                      lower_bound=lower_bound, upper_bound=upper_bound)


_KV_PAIR_DELIMITER = '='


class HostPort(object):
  """A class for holding host and port information."""

  def __init__(self, host, port):
    self.host = host
    self.port = port

  @staticmethod
  def Parse(s):
    """Parse the given string into a HostPort object.

    This can be used as an argparse type.

    Args:
      s: str, The string to parse.

    Raises:
      ArgumentTypeError: If the string is not valid.

    Returns:
      HostPort, The parsed object.
    """
    if not s:
      return HostPort(None, None)
    if ':' not in s:
      return HostPort(s, None)
    parts = s.split(':')
    if len(parts) > 2:
      raise ArgumentTypeError(
          _GenerateErrorMessage('Failed to parse host and port', user_input=s))
    return HostPort(parts[0] or None, parts[1] or None)


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
    # TODO(filipjs): Add timezone support.
    for date_format in accepted_formats:
      try:
        return datetime.datetime.strptime(s, date_format)
      except ValueError:
        pass
    raise ArgumentTypeError(
        _GenerateErrorMessage(
            'Failed to parse date. Value should be in ISO or RFC3339 format',
            user_input=s))


def BoundedInt(lower_bound=None, upper_bound=None):
  """Returns a function that can parse integers within some bound."""

  def _Parse(value):
    """Parses value as an int, raising ArgumentTypeError if out of bounds."""
    v = int(value)

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

  return _Parse


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

    # TODO(jasmuth): These exceptions won't present well to the user.
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
      # TODO(jasmuth): These exceptions won't present well to the user.
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

    Provides a error for users who type (or have a script) that specifies a list
    with the elements in different arguments. eg.
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

    # TODO(cherba): remove this.
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
      if not values and switch_value is not None:
        super(FloatingListValuesCatcherAction, self).__call__(
            parser, namespace, switch_value, option_string=option_string)
        return

      if len(values) > 1:

        class ArgShell(object):
          """Class designed to trick argparse into displaying a nice error."""

          def __init__(self, name):
            self.option_strings = [name]

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

        # TODO(jasmuth): stop warning when we're ready
        warn_only = True

        if not warn_only:
          raise argparse.ArgumentError(ArgShell(option_string), msg)
        else:
          log.warn(msg)

        super(FloatingListValuesCatcherAction, self).__call__(
            parser, namespace, aggregate_value, option_string=option_string)
      else:
        super(FloatingListValuesCatcherAction, self).__call__(
            parser, namespace, values[0], option_string=option_string)

  return FloatingListValuesCatcherAction
