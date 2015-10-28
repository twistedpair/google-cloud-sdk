# Copyright 2015 Google Inc. All Rights Reserved.

"""Built-in resource transform functions.

A resource transform function converts a JSON-serializable resource to a string
value. This module contains built-in transform functions that may be used in
resource projection and filter expressions.

NOTICE: Each TransformFoo() method is the implementation of a foo() transform
function. Even though the implementation here is in Python the usage in resource
projection and filter expressions is language agnostic. This affects the
Pythonicness of the Transform*() methods:
  (1) The docstrings are used to generate external user documentation.
  (2) The method prototypes are included in the documentation. In particular the
      prototype formal parameter names are stylized for the documentation.
  (3) The types of some args, like r, are not fixed until runtime. Other args
      may have either a base type value or string representation of that type.
      It is up to the transform implementation to silently do the string=>type
      conversions. That's why you may see e.g. int(arg) in some of the methods.
  (4) Unless it is documented to do so, a transform function must not raise any
      exceptions related to the resource r. The `undefined' arg is used to
      handle all unusual conditions, including ones that would raise exceptions.
      Exceptions for arguments explicitly under the caller's control are OK.
"""

import cStringIO
import datetime
import re

from googlecloudsdk.core.console import console_attr
from googlecloudsdk.core.resource import resource_exceptions
from googlecloudsdk.core.resource import resource_projector
from googlecloudsdk.core.resource import resource_property
from googlecloudsdk.core.util import timezone


def TransformAlways(r):
  """Marks a transform sequence to always be applied.

  In some cases transforms are disabled. Prepending always() to a transform
  sequence causes the sequence to always be evaluated.

  Example:
    some_field.always().foo().bar() will always apply foo() and then bar().

  Args:
    r: A resource.

  Returns:
    r.
  """
  # This method is used as a decorator in transform expressions. It is
  # recognized at parse time and discarded.
  return r


def TransformBaseName(r, undefined=''):
  """Returns the last path component in r.

  Args:
    r: A URI or unix/windows file path.
    undefined: This value is returned if r or the basename is empty.

  Returns:
    The last path component.
  """
  if not r:
    return undefined
  s = str(r)
  for separator in ('/', '\\'):
    i = s.rfind(separator)
    if i >= 0:
      return s[i + 1:]
  return s or undefined


def TransformColor(r, red=None, yellow=None, green=None, blue=None, **kwargs):
  """Colorizes the string value of r.

  The resource string is searched for an re pattern match in Roy.G.Biv order.
  The first pattern that matches colorizes the resource string with that color.

  Args:
    r: A JSON-serializable object.
    red: Color red resource value pattern.
    yellow: Color yellow resource value pattern.
    green: Color green resource value pattern.
    blue: Color blue resource value pattern.
    **kwargs: console_attr.Colorizer() kwargs.

  Returns:
    A console_attr.Colorizer() object if any color substring matches, r
    otherwise.
  """
  string = str(r)
  for color, pattern in (('red', red), ('yellow', yellow), ('green', green),
                         ('blue', blue)):
    if pattern and re.search(pattern, string):
      return console_attr.Colorizer(string, color, **kwargs)
  return string


# pylint: disable=redefined-builtin, external expression expects format kwarg.
def TransformDate(r, format='%Y-%m-%dT%H:%M:%S', unit=1, undefined='', tz=None):
  """Formats r to a strftime() format.

  Args:
    r: A timestamp number or an object with 3 or more of these fields: year,
      month, day, hour, minute, second, millisecond, microsecond, nanosecond.
    format: The strftime(3) format.
    unit: Timestamp r divided by unit yields seconds.
    undefined: Returns this if r does not contain a valid time.
    tz: Fixed timezone string, local timezone if None. For example, EST5EDT,
      US/Pacific, UTC, WEST.

  Returns:
    The strftime() date format for r or undefined if r does not contain a valid
    time.
  """
  tz = timezone.GetTimeZone(tz)
  # Check if r is a timestamp.
  try:
    timestamp = float(r) / float(unit)
    dt = datetime.datetime.fromtimestamp(timestamp, tz)
    return dt.strftime(format)
  except (TypeError, ValueError):
    pass

  def _FormatFromParts():
    """Returns the formatted time from broken down time parts in r.

    Raises:
      TypeError: For invalid time part errors.
      ValueError: For time conversion errors or not enough valid time parts.

    Returns:
      The formatted time from broken down time parts in r.
    """
    valid = 0
    parts = []
    now = datetime.datetime.now(tz)
    for part in ('year', 'month', 'day', 'hour', 'minute', 'second'):
      value = resource_property.Get(r, [part], None)
      if value is None:
        # Missing parts default to now.
        value = getattr(now, part)
      else:
        valid += 1
      parts.append(int(value))
    # The last value is microseconds. Add in any subsecond parts but don't count
    # them in the validity check.
    parts.append(0)
    for i, part in enumerate(['nanosecond', 'microsecond', 'millisecond']):
      value = resource_property.Get(r, [part], None)
      if value is not None:
        parts[-1] += int(int(value) * 1000 ** (i - 1))
    # year&month&day or hour&minute&second would be OK, "3" covers those and any
    # combination of 3 non-subsecond date/time parts.
    if valid < 3:
      raise ValueError
    parts.append(tz)
    dt = datetime.datetime(*parts)
    return dt.strftime(format)

  try:
    return _FormatFromParts()
  except (TypeError, ValueError):
    pass

  # Does anyone really know what time it is?
  return undefined


def TransformDuration(r, unit=1, undefined=''):
  """Formats r to a duration string.

  Args:
    r: A JSON-serializable object.
    unit: r divided by unit yields seconds.
    undefined: Returns this if r/unit is not a valid timestamp.

  Returns:
    The duration string for r or undefined if r is not a duration.
  """
  try:
    timestamp = float(r) / unit
    d = datetime.timedelta(seconds=timestamp)
    return str(d).replace(' ', '')
  except (TypeError, ValueError):
    return undefined


def TransformError(r, message=None):
  """Raises an Error exception that does not generate a stack trace.

  Args:
    r: A JSON-serializable object.
    message: An error message. If None then r is formatted as the error message.

  Raises:
    Error: This will not generate a stack trace.
  """
  raise resource_exceptions.Error(message if message is not None else str(r))


def TransformFatal(r, message=None):
  """Raises an InternalError exception that generates a stack trace.

  Args:
    r: A JSON-serializable object.
    message: An error message. If None then r is formatted as the error message.

  Raises:
    InternalError: This generates a stack trace.
  """
  raise resource_exceptions.InternalError(message if message is not None
                                          else str(r))


def TransformFirstOf(r, *args):
  """Returns the first non-empty r.name value for name in args.

  Args:
    r: A JSON-serializable object.
    *args: Names to check for values in r.

  Returns:
    The first non-empty r.name value for name in args, '' otherwise.

  Example:
    x.firstof(bar_foo, barFoo, BarFoo, BAR_FOO) will check x.bar_foo, x.barFoo,
    x.BarFoo, and x.BAR_FOO in order for the first non-empty value.
  """
  for name in args:
    v = resource_property.Get(r, [name], None)
    if v is not None:
      return v
  return ''


# The 'format' transform is special: it has no kwargs and the second argument
# is the ProjectionSpec of the calling projection.
def TransformFormat(r, projection, fmt, *args):
  """Formats a sub-projection of r.

  Args:
    r: A JSON-serializable object.
    projection: The parent ProjectionSpec.
    fmt: The format string with {0} ... {nargs-1} references to the resource
      key arg values.
    *args: The resource key args to format. The args values form a projection on
      r. The projection symbols and aliases are available in the sub-projection.

  Returns:
    The formatted string.

  Example:
    --format='value(format("{0:f.1}/{0:f.1}", q.CPU.default, q.CPU.limit))'
  """
  columns = resource_projector.Compile('(' + ','.join(args) + ')',
                                       by_columns=True,
                                       defaults=projection).Evaluate(r)
  return fmt.format(*columns)


def TransformGroup(r, *args):
  """Formats a [...] grouped list.

  Each group is enclosed in [...]. The first item separator is ':', subsequent
  separators are ','.
    [item1] [item1] ...
    [item1: item2] ... [item1: item2]
    [item1: item2, item3] ... [item1: item2, item3]

  Args:
    r: A JSON-serializable object.
    *args: Optional attribute names to select from the list. Otherwise
      the string value of each list item is selected.

  Returns:
    The [...] grouped formatted list, [] if r is empty.
  """
  if not r:
    return '[]'
  buf = cStringIO.StringIO()
  sep = None
  for item in r:
    if sep:
      buf.write(sep)
    else:
      sep = ' '
    if not args:
      buf.write('[{0}]'.format(str(item)))
    else:
      buf.write('[')
      sub = None
      for attr in args:
        if sub:
          buf.write(sub)
          sub = ', '
        else:
          sub = ': '
        buf.write(str(getattr(item, attr)))
      buf.write(']')
  return buf.getvalue()


def TransformIso(r, undefined='T'):
  """Formats r to the numeric ISO time format.

  Args:
    r: A JSON-serializable object.
    undefined: Returns this if r does not have an isoformat() attribute.

  Returns:
    The numeric ISO time format for r or undefined if r is not a time.
  """
  return r.isoformat() if hasattr(r, 'isoformat') else undefined


def TransformLen(r):
  """Returns the length of r if r is non-empty, 0 otherwise.

  Args:
    r: A JSON-serializable object.

  Returns:
    The length of r if r is non-empty, 0 otherwise.
  """
  try:
    return len(r)
  except TypeError:
    return 0


def TransformList(r, undefined='', separator=','):
  """Formats a dict or list into a compact comma separated list.

  Args:
    r: A JSON-serializable object.
    undefined: Return this if r is empty.
    separator: The list item separator string.

  Returns:
    The key=value pairs for a dict or list values for a list, separated by
    separator. Returns undefined if r is empty, or r if it is not a dict or
    list.
  """
  if isinstance(r, dict):
    return separator.join(['{key}={value}'.format(key=key, value=value)
                           for key, value in sorted(r.iteritems())])
  if isinstance(r, list):
    return separator.join(map(str, r))
  return r or undefined


def TransformMap(r):
  """Applies the next transform in the sequence to each item in list resource r.

  Example:
    list_field.map().foo().bar() applies foo() to each item in list_field and
    then bar() to the resulting value. list_field.map().foo().map().bar()
    applies foo() to each item in list_field and then bar() to each item in the
    resulting list.

  Args:
    r: A resource.

  Returns:
    r.
  """
  # This method is used as a decorator in transform expressions. It is
  # recognized at parse time and discarded.
  return r


def TransformResolution(r, undefined='', transpose=False):
  """Formats a human readable XY resolution.

  Args:
    r: object, A JSON-serializable object containing an x/y resolution.
    undefined: Returns this if a recognizable resolution was not found.
    transpose: Returns the y/x resolution if True.

  Returns:
    The human readable x/y resolution for r if it contains members that
      specify width/height, col/row, col/line, or x/y resolution. Returns
      undefined if no resolution found.
  """
  names = (
      ('width', 'height'),
      ('screenx', 'screeny'),
      ('col', 'row'),
      ('col', 'line'),
      ('x', 'y'),
      )

  # Collect the lower case candidate member names.
  mem = {}
  for m in r if isinstance(r, dict) else dir(r):
    if not m.startswith('__') and not m.endswith('__'):
      mem[m.lower()] = m

  def _Dimension(d):
    """Gets the resolution dimension for d.

    Args:
      d: The dimension name substring to get.

    Returns:
      The resolution dimension matching d or None.
    """
    for m in mem:
      if d in m:
        return resource_property.Get(r, [mem[d]], None)
    return None

  # Check member name pairwise matches in order from least to most ambiguous.
  for name_x, name_y in names:
    x = _Dimension(name_x)
    if x is None:
      continue
    y = _Dimension(name_y)
    if y is None:
      continue
    return ('{y} x {x}' if transpose else '{x} x {y}').format(x=x, y=y)
  return undefined


def TransformScope(r, *args):
  """Gets the /args/ suffix from URI r.

  Args:
    r: A URI.
    *args: Optional URI segment names. If not specified then 'regions', 'zones'
      is assumed.

  Returns:
    The URI segment after the first /*args/ in r, the last /-separated
      component in r if none found.

  Example:
    scope('https://abc/foo/projects/bar/zyx', 'projects') returns 'bar/xyz'.
    scope("https://abc/foo/rergions/abc") returns 'abc'.
  """
  if not r:
    return ''
  if '/' not in r:
    return r
  # Checking for regions and/or zones is the most common use case.
  for scope in args or ('regions', 'zones'):
    segment = '/' + scope + '/'
    if segment in r:
      return r.split(segment)[-1]
  if r.startswith('https://'):
    return r.split('/')[-1]
  return r


def TransformSegment(r, index=-1, undefined=''):
  """Returns the index-th URI path segment in r.

  Args:
    r: A URI path.
    index: The path segment index to return counting from 0.
    undefined: This value is returned if r or segment index is empty.

  Returns:
    The index-th URI path segment in r
  """
  if not r:
    return undefined
  s = str(r)
  segments = s.split('/')
  try:
    return segments[int(index)] or undefined
  except IndexError:
    return undefined


# pylint: disable=redefined-builtin, params match the transform spec
def TransformSize(r, zero='0', units_in=None, units_out=None, min=0):
  """Formats a human readable size in bytes.

  Args:
    r: A size in bytes.
    zero: Returns this if size==0. Ignored if None.
    units_in: A unit suffix (only the first character is checked) or unit size.
      The size of r is multiplied by this size. The defaults is 1.0.
    units_out: A unit suffix (only the first character is checked) or unit size.
      The size of r is divided by this size. The defaults is 1.0.
    min: Sizes < min will be listed as "< MIN".

  Returns:
    A human readable scaled size in bytes.
  """

  def _UnitSuffixAndSize(unit):
    """Returns the unit size for unit, 1.0 for unknown units.

    Args:
      unit: The unit suffix (only the first character is checked), the unit
        size in bytes, or None.

    Returns:
      A (unit_suffix, unit_size) tuple.
    """
    unit_size = {
        'K': 2 ** 10,
        'M': 2 ** 20,
        'G': 2 ** 30,
        'T': 2 ** 40,
        'P': 2 ** 50,
    }

    try:
      return ('', float(unit) or 1.0)
    except (TypeError, ValueError):
      pass
    try:
      unit_suffix = unit[0].upper()
      return (unit_suffix, unit_size[unit_suffix])
    except (IndexError, KeyError, TypeError):
      pass
    return ('', 1.0)

  if not r and zero is not None:
    return zero
  try:
    size = float(r)
  except (TypeError, ValueError):
    size = 0
  min_size = float(min)  # Exception OK here.
  if size < min_size:
    size = min_size
    prefix = '< '
  else:
    prefix = ''
  (_, units_in_size) = _UnitSuffixAndSize(units_in)
  size *= units_in_size
  (units_out_suffix, units_out_size) = _UnitSuffixAndSize(units_out)
  if units_out_suffix:
    size /= units_out_size
    return '{0:.1f}'.format(size)
  the_unit = 'PiB'
  for unit in ['bytes', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB']:
    if size < 1024.0:
      the_unit = unit
      break
    size /= 1024.0
  if the_unit:
    the_unit = ' ' + the_unit
  if size == int(size):
    return '{0}{1}{2}'.format(prefix, int(size), the_unit)
  else:
    return '{0}{1:.1f}{2}'.format(prefix, size, the_unit)


def TransformUri(r, undefined='.'):
  """Gets the URI for r.

  Args:
    r: A JSON-serializable object.
    undefined: Returns this if a the URI for r cannot be determined.

  Returns:
    The URI for r or undefined if not defined.
  """

  names = ('selfLink', 'SelfLink', 'instance')

  def _GetAttr(attr):
    """Returns the string value for attr or None if the value is not a string.

    Args:
      attr: The attribute object to get the value from.

    Returns:
      The string value for attr or None if the value is not a string.
    """
    try:
      attr = attr()
    except TypeError:
      pass
    return attr if isinstance(attr, (basestring, buffer)) else None

  if isinstance(r, (basestring, buffer)):
    if r.startswith('https://'):
      return r
  elif r:
    for name in names:
      attr = _GetAttr(resource_property.Get(r, [name], None))
      if attr:
        return attr
  return undefined


def TransformYesNo(r, yes=None, no='No'):
  """Returns no if r is empty, yes or r otherwise.

  Args:
    r: A JSON-serializable object.
    yes: If r is not empty then returns yes or r.
    no: Returns this string if r is empty.

  Returns:
    yes or r if r is not empty, no otherwise.
  """
  return (r if yes is None else yes) if r else no


# The builtin transforms.
_BUILTIN_TRANSFORMS = {
    'always': TransformAlways,
    'basename': TransformBaseName,
    'color': TransformColor,
    'date': TransformDate,
    'duration': TransformDuration,
    'error': TransformError,
    'fatal': TransformFatal,
    'firstof': TransformFirstOf,
    'format': TransformFormat,
    'group': TransformGroup,
    'iso': TransformIso,
    'len': TransformLen,
    'list': TransformList,
    'map': TransformMap,
    'resolution': TransformResolution,
    'scope': TransformScope,
    'segment': TransformSegment,
    'size': TransformSize,
    'uri': TransformUri,
    'yesno': TransformYesNo,
}

# This dict maps API names (the leftmost dotted name in a collection) to
# (module_path, method_name) tuples where:
#   module_path: A dotted module path that contains a transform dict.
#   method_name: A method name in the module that returns the transform dict.
_API_TO_TRANSFORMS = {
    'compute': ('googlecloudsdk.api_lib.compute.transforms', 'GetTransforms'),
}


def GetTransforms(collection=None):
  """Returns the builtin or collection specific transform symbols dict.

  Args:
    collection: A collection, None or 'builtin' for the builtin transforms.

  Raises:
    ImportError: module_path __import__ error.
    AttributeError: module does not contain method_name.

  Returns:
    The transform symbols dict, None if there is none.
  """
  if collection in (None, 'builtin'):
    return _BUILTIN_TRANSFORMS
  api = collection.split('.')[0]
  module_path, method_name = _API_TO_TRANSFORMS.get(api, (None, None))
  if not module_path:
    return None
  # Exceptions after this point indicate configuration/installation errors.
  module = __import__(module_path, fromlist=[method_name])
  method = getattr(module, method_name)
  return method()
