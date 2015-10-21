# Copyright 2015 Google Inc. All Rights Reserved.

"""datetime module timezone support.

The datetime module by design only provides abc (abstract base class) timezone
support. This module provides concrete timezone support by deferring to the time
module which provides full timezone support by default. Its incredible that
every Python project is forced to repeat this dance. Examples from the official
online Python docs take the wrong approach by trying (and failing) to replicate
what the time module already does. pytz looks promising, but it forces the
caller to use two pytz invented methods to get the datetime method to work. Its
a big mess. One last fly in the ointment is Windows which currently only has
system wide timezone control and no time.tzset(). A process cannot operate in
its own timezone and use the system time libraries. The _TimzoneNoTzset method
comes close to working. Its flaw is that it defers to the time.localtime() to
determine std vs. dst time. This means that it will be accurate for timezones in
the same region as time.localtime() (e.g., all US timezones), but will be
"close" for regions outside the local region.
"""

import datetime
import os
import re
import time


class _TimeZoneTzset(datetime.tzinfo):
  """A tzinfo for a given TZ name based on the local system DB using tzset().

  This is an instantiation of the datetime.tzinfo abc module.

  This is the preferred method because it relies on time.localtime() which on
  most systems references a standard timezone DB.

  This is an ugly module because the low level time methods key off the
  environment instead of timezone handles. They never expected one program to
  deal with more than one timezone. The code here makes the datetime module,
  which does support handles (datetime.tzinfo methods), work with mutiple
  timezones. However, because of the environment hackery it's not thread safe.
  """

  _ZERO = datetime.timedelta(0)

  def __init__(self, tz):
    """Initializer.

    Args:
      tz: The TZ name, e.g., US/Eastern, EST5EDT, US/Pacific, PST8PDT.
    """
    super(_TimeZoneTzset, self).__init__()
    self._in_dst = False
    self._tz = tz

    try:
      old_tz = os.environ.get('TZ')
      os.environ['TZ'] = tz
      time.tzset()
      self._std_name = time.tzname[0]
      self._dst_name = time.tzname[1]
      self._std_offset = datetime.timedelta(seconds=-time.timezone)
      if time.daylight:
        self._dst_offset = datetime.timedelta(seconds=-time.altzone)
      else:
        self._dst_offset = self._std_offset
      self._dst_diff = self._dst_offset - self._std_offset
    finally:
      if old_tz is not None:
        os.environ['TZ'] = old_tz
      else:
        os.environ.pop('TZ')
      time.tzset()

  def __repr__(self):
    return self._tz

  def tzname(self, dt):
    """Returns the daylight savings or standard timezone name.

    Args:
      dt: A datetime.datetime object.

    Returns:
      The daylight savings timezone name if dt is in a daylight savings range
      for the timezone, otherwise the standard timezone name.
    """
    return self._dst_name if self.dst(dt) else self._std_name

  def utcoffset(self, dt):
    """Returns the daylight savings or standard timezone UTC offset.

    Args:
      dt: A datetime.datetime object.

    Returns:
      A datetime.timedelta() of the daylight savings timezone UTC offset if dt
      is in a daylight savings range for the timezone, otherwise a
      datetime.timedelta() of the standard timezone UTC offset.
    """
    return self._dst_offset if self.dst(dt) else self._std_offset

  def dst(self, dt):
    """Returns the daylight savings offset or the 0 offset.

    Args:
      dt: A datetime.datetime object.

    Returns:
      A datetime.timedelta() of the daylight savings offset if dt is in a
      daylight savings range for the timezone, otherwise timedelta(0).
    """
    # dt.timetuple() does a recursive call on dt.dst() which gets us right
    # back here. self._in_dst stops the recursion and returns a value that
    # is eventually ignored anyway. time.localtime() gets the tm.tm_isdst
    # value we can trust.
    if self._in_dst:
      return self._ZERO
    self._in_dst = True
    tm = dt.timetuple()

    try:
      old_tz = os.environ.get('TZ')
      os.environ['TZ'] = self._tz
      time.tzset()
      # No datetime methods here! The time module is the timezone oracle.
      tm = time.localtime(time.mktime(tm))
    finally:
      if old_tz is not None:
        os.environ['TZ'] = old_tz
      else:
        os.environ.pop('TZ')
      time.tzset()

    self._in_dst = False
    return self._dst_diff if tm.tm_isdst else self._ZERO


class _TimeZoneNoTzset(datetime.tzinfo):
  """A tzinfo for a given TZ name based on the local system without tzset().

  This is an instantiation of the datetime.tzinfo abc module.

  This is a workaround for systems without tzset() where _TimeZoneTzset does not
  work.

  Systems without tzset() probably have only system wide timezone control.
  The workaround here uses the local timezone dst algorithm. This is
  imperfect and will barely work in timezones within the same region. It will
  however work for US timezones when the local timezone is also in the US.
  """

  _TZ_ALIAS = {
      'us/eastern': 'EST5EDT',
      'us/central': 'CST6CDT',
      'us/mountain': 'MST7MDT',
      'us/pacific': 'PST8PDT',
      'hawaii-aleutian': 'HAST10HADT',
      'eastern european': 'EET+2EEDT',
      'central european': 'CET+1CEDT',
      'western european': 'WET+0WEDT',
      'australian eastern': 'AEST+10AEDT',
      'australian central': 'ACST+09:30ACDT',
      'australian western': 'AWST+08AWDT',
      'indian': 'IST+05:30',
      }

  _ZERO = datetime.timedelta(0)

  def __init__(self, tz):
    """Initializer.

    Args:
      tz: The TZ name, e.g., US/Eastern, EST5EDT, US/Pacific, PST8PDT.

    Raises:
      ValueError: if the timezone is unknown or not in the form
        <STD-name>[-+]<STD-hours-west>[:<STD-minutes-west>]<DST-name>.
    """
    super(_TimeZoneNoTzset, self).__init__()
    self._in_dst = False
    self._tz = tz
    expr = self._TZ_ALIAS.get(tz.lower(), tz)
    # Split the TZ expression into 4 parts:
    # (1) standard time abbreviation
    # (2) +: east of GMT, empty or -: west of GMT
    # (3) hours[:minutes[:seconds]] GMT offset
    # (4) optional daylight savings time abbreviation
    match = re.match(r'([^-+\d]*)([-+]?)([:\d]+)(\D*)', expr)
    if not match:
      raise ValueError('Unknown timezone [{0}].'.format(tz))
    self._std_name = match.group(1)
    self._dst_name = match.group(4)
    offset = match.group(3)
    minutes_west = 0
    for i, offset_part in enumerate(offset.split(':')):
      minutes_west += int(offset_part) * 60 ** (1 - i)
    if match.group(2) != '+':
      minutes_west = -minutes_west
    self._std_offset = datetime.timedelta(minutes=minutes_west)
    if time.daylight:
      self._dst_offset = datetime.timedelta(minutes=minutes_west + 60)
    else:
      self._dst_offset = self._std_offset
    self._dst_diff = self._dst_offset - self._std_offset

  def __repr__(self):
    return self._tz

  def tzname(self, dt):
    """Returns the daylight savings or standard timezone name.

    Args:
      dt: A datetime.datetime object.

    Returns:
      The daylight savings timezone name if dt is in a daylight savings range
      for the timezone, otherwise the standard timezone name.
    """
    return self._dst_name if self.dst(dt) else self._std_name

  def utcoffset(self, dt):
    """Returns the daylight savings or standard timezone UTC offset.

    Args:
      dt: A datetime.datetime object.

    Returns:
      A datetime.timedelta() of the daylight savings timezone UTC offset if dt
      is in a daylight savings range for the timezone, otherwise a
      datetime.timedelta() of the standard timezone UTC offset.
    """
    return self._dst_offset if self.dst(dt) else self._std_offset

  def dst(self, dt):
    """Returns the daylight savings offset or the 0 offset.

    Args:
      dt: A datetime.datetime object.

    Returns:
      A datetime.timedelta() of the daylight savings offset if dt is in a
      daylight savings range for the timezone, otherwise timedelta(0).
    """
    if not self._dst_name:
      return self._ZERO
    # dt.timetuple() does a recursive call on dt.dst() which gets us right
    # back here. self._in_dst stops the recursion and returns a value that
    # is eventually ignored anyway. time.localtime() gets the tm.tm_isdst
    # value we can trust.
    if self._in_dst:
      return self._ZERO
    self._in_dst = True
    tm = dt.timetuple()
    # No datetime methods here! The time module is the dst oracle.
    tm = time.localtime(time.mktime(tm))
    self._in_dst = False
    return self._dst_diff if tm.tm_isdst else self._ZERO


# pylint: disable=invalid-name
_TimeZone = _TimeZoneTzset if hasattr(time, 'tzset') else _TimeZoneNoTzset


class _UTCTimeZone(datetime.tzinfo):
  """The UTC tzinfo.

  This is an instantiation of the datetime.tzinfo abc module. See _TimeZone
  above for detailed docstrings.
  """

  _ZERO = datetime.timedelta(0)

  def __init__(self):
    super(_UTCTimeZone, self).__init__()
    self._tz = 'UTC'

  def __repr__(self):
    return self._tz

  def tzname(self, unused_dt):
    return self._tz

  def utcoffset(self, unused_dt):
    return self._ZERO

  def dst(self, unused_dt):
    return self._ZERO


_TIMEZONES = {'UTC': _UTCTimeZone()}


def GetTimeZone(tz):
  """Returns a datetime.tzinfo object for tz.

  Args:
    tz: A timezone string, e.g., 'US/Eastern', 'EST5EDT', 'US/Pacific'.

  Returns:
    A datetime.tzinfo object for tz, None if tz is None or empty.
  """
  if not tz:
    return None
  if tz in _TIMEZONES:
    return _TIMEZONES[tz]
  timezone = _TimeZone(tz)
  _TIMEZONES[tz] = timezone
  return timezone
