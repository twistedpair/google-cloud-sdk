# Copyright 2015 Google Inc. All Rights Reserved.
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
"""Utilities for working with time and timestamps."""

import calendar
import re
import time


_DISPLAY_FORMAT = '%Y-%m-%d %H:%M:%S'


# Parsing code for rfc3339 timestamps, taken from rfc3339.py


def Strptime(rfc3339_str):
  """Converts an RFC 3339 timestamp to Unix time in seconds since the epoch.

  Args:
    rfc3339_str: a timestamp in RFC 3339 format (yyyy-mm-ddThh:mm:ss.sss
        followed by a time zone, given as Z, +hh:mm, or -hh:mm)

  Returns:
    a number of seconds since January 1, 1970, 00:00:00 UTC

  Raises:
    ValueError: if the timestamp is not in an acceptable format
  """
  match = re.match(r'(\d\d\d\d)-(\d\d)-(\d\d)T'
                   r'(\d\d):(\d\d):(\d\d)(?:\.(\d+))?'
                   r'(?:(Z)|([-+])(\d\d):(\d\d))', rfc3339_str)
  if not match:
    raise ValueError('not a valid timestamp: %r' % rfc3339_str)

  (year, month, day, hour, minute, second, frac_seconds,
   zulu, zone_sign, zone_hours, zone_minutes) = match.groups()

  time_tuple = map(int, [year, month, day, hour, minute, second])

  # Parse the time zone offset.
  if zulu == 'Z':  # explicit
    zone_offset = 0
  else:
    zone_offset = int(zone_hours) * 3600 + int(zone_minutes) * 60
    if zone_sign == '-':
      zone_offset = -zone_offset

  integer_time = calendar.timegm(time_tuple) - zone_offset
  if frac_seconds:
    sig_dig = len(frac_seconds)
    return ((integer_time * (10 ** sig_dig) + int(frac_seconds)) *
            (10 ** -sig_dig))
  else:
    return integer_time


def FormatTimestamp(rfc3339_str):
  """Formats the timestamp encoded in the rfc3339 timestamp.

  Args:
    rfc3339_str: a timestamp in RFC 3339 format (yyyy-mm-ddThh:mm:ss.sss
      followed by a time zone, given as Z, +hh:mm or -hh:mm), or None

  Returns:
    a string in the form yyyy-mm-dd hh:mm:ss, or None (if the original
    timestamp was None or the epoch).

  Raises:
    ValueError: if the timestamp is not in an acceptable format
  """
  if not rfc3339_str:
    return None
  parsed_time = Strptime(rfc3339_str)
  if not parsed_time:
    return None
  return time.strftime(_DISPLAY_FORMAT, time.localtime(parsed_time))


def Strftime(unix_time):
  """Converts a Unix time to an RFC 3339 timestamp in UTC.

  Note that fractions less than a millisecond are truncated.

  Args:
    unix_time: seconds (int or float) since January 1, 1970, 00:00:00 UTC

  Returns:
    a timestamp in RFC 3339 format (yyyy-mm-ddThh:mm:ss.sssZ)
  """
  year, month, day, hour, minute, second = time.gmtime(unix_time)[:6]
  milliseconds = int(unix_time * 1000) - (int(unix_time) * 1000)
  return '%04d-%02d-%02dT%02d:%02d:%02d.%03dZ' % (
      year, month, day, hour, minute, second, milliseconds)


def ParseTimeArg(arg):
  """Parses a time argument and returns it as seconds since epoch.

  Args:
    arg: Time specified in yyyy-mm-dd hh:mm:ss format.
  Returns:
    Seconds since the epoch, in floating point.
  """
  return time.mktime(time.strptime(arg, _DISPLAY_FORMAT))
