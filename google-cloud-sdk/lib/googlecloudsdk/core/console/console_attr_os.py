# Copyright 2015 Google Inc. All Rights Reserved.

"""OS specific console_attr helper functions."""

import os
import sys


def GetTermSize():
  """Gets the terminal x and y dimensions in characters.

  _GetTermSize*() helper functions taken from:
    http://stackoverflow.com/questions/263890/

  Returns:
    (columns, lines): A tuple containing the terminal x and y dimensions.
  """
  xy = None
  # Believe the first helper that doesn't bail.
  for get_terminal_size in (_GetTermSizePosix,
                            _GetTermSizeWindows,
                            _GetTermSizeEnvironment,
                            _GetTermSizeTput):
    try:
      xy = get_terminal_size()
      if xy:
        break
    except:  # pylint: disable=bare-except
      pass
  return xy or (80, 24)


def _GetTermSizePosix():
  """Returns the Posix terminal x and y dimensions."""
  # pylint: disable=g-import-not-at-top
  import fcntl
  # pylint: disable=g-import-not-at-top
  import struct
  # pylint: disable=g-import-not-at-top
  import termios

  def _GetXY(fd):
    """Returns the terminal (x,y) size for fd.

    Args:
      fd: The terminal file descriptor.

    Returns:
      The terminal (x,y) size for fd or None on error.
    """
    try:
      # This magic incantation converts a struct from ioctl(2) containing two
      # binary shorts to a (rows, columns) int tuple.
      rc = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
      return (rc[1], rc[0]) if rc else None
    except:  # pylint: disable=bare-except
      return None

  xy = _GetXY(0) or _GetXY(1) or _GetXY(2)
  if not xy:
    fd = None
    try:
      fd = os.open(os.ctermid(), os.O_RDONLY)
      xy = _GetXY(fd)
    except:  # pylint: disable=bare-except
      xy = None
    finally:
      if fd is not None:
        os.close(fd)
  return xy


def _GetTermSizeWindows():
  """Returns the Windows terminal x and y dimensions."""
  # pylint:disable=g-import-not-at-top
  import struct
  # pylint: disable=g-import-not-at-top
  from ctypes import create_string_buffer
  # pylint:disable=g-import-not-at-top
  from ctypes import windll

  # stdin handle is -10
  # stdout handle is -11
  # stderr handle is -12

  h = windll.kernel32.GetStdHandle(-12)
  csbi = create_string_buffer(22)
  if not windll.kernel32.GetConsoleScreenBufferInfo(h, csbi):
    return None
  (unused_bufx, unused_bufy, unused_curx, unused_cury, unused_wattr,
   left, top, right, bottom,
   unused_maxx, unused_maxy) = struct.unpack('hhhhHhhhhhh', csbi.raw)
  x = right - left + 1
  y = bottom - top + 1
  return (x, y)


def _GetTermSizeEnvironment():
  """Returns the terminal x and y dimensions from the environment."""
  return (int(os.environ['COLUMNS']), int(os.environ['LINES']))


def _GetTermSizeTput():
  """Returns the terminal x and y dimemsions from tput(1)."""
  # pylint: disable=g-import-not-at-top
  from googlecloudsdk.core.util.compat26 import subprocess
  output = subprocess.check_output(['tput', 'cols'], stderr=subprocess.STDOUT)
  cols = int(output)
  output = subprocess.check_output(['tput', 'lines'], stderr=subprocess.STDOUT)
  rows = int(output)
  return (cols, rows)


def GetRawCharFunction():
  """Returns a function that reads one character from stdin with no echo.

  Returns:
    A function that reads one character from stdin with no echo or a function
    that always returns None if stdin does not support it.
  """
  # Believe the first helper that doesn't bail.
  for get_raw_char_function in (_GetRawCharFunctionPosix,
                                _GetRawCharFunctionWindows):
    try:
      return get_raw_char_function()
    except:  # pylint: disable=bare-except
      pass
  return lambda: None


def _GetRawCharFunctionPosix():
  """_GetRawCharFunction helper using Posix APIs."""
  # pylint: disable=g-import-not-at-top
  import tty
  # pylint: disable=g-import-not-at-top
  import termios

  def _GetRawCharPosix():
    """Reads one char from stdin without echo using Posix APIs.

    Returns:
      One character, None on EOF (^D or ^Z) or error.
    """
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
      tty.setraw(fd)
      c = sys.stdin.read(1)
    except:  # pylint:disable=bare-except
      c = None
    finally:
      termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return None if c in ('\x04', '\x1a') else c

  return _GetRawCharPosix


def _GetRawCharFunctionWindows():
  """_GetRawCharFunction helper using Windows APIs."""
  # pylint: disable=g-import-not-at-top
  import msvcrt

  def _GetRawCharWindows():
    """Reads one char from stdin without echo using Windows APIs.

    Returns:
      One character, None on EOF (^D or ^Z).
    """
    c = msvcrt.getch()
    # Special function key is a two character sequence; return the second char.
    if c in ('\x00', '\xe0'):
      c = msvcrt.getch()
    return None if c in ('\x04', '\x1a') else c

  return _GetRawCharWindows
