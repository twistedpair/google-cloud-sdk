# -*- coding: utf-8 -*- #

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

r"""A module for console attributes, special characters and functions.

The target architectures {linux, macos, windows} support inline encoding for
all attributes except color. Windows requires win32 calls to manipulate the
console color state.

Usage:

  # Get the console attribute state.
  out = log.out
  con = console_attr.GetConsoleAttr(out=out)

  # Get the ISO 8879:1986//ENTITIES Box and Line Drawing characters.
  box = con.GetBoxLineCharacters()
  # Print an X inside a box.
  out.write(box.dr)
  out.write(box.h)
  out.write(box.dl)
  out.write('\n')
  out.write(box.v)
  out.write('X')
  out.write(box.v)
  out.write('\n')
  out.write(box.ur)
  out.write(box.h)
  out.write(box.ul)
  out.write('\n')

  # Print the bullet characters.
  for c in con.GetBullets():
    out.write(c)
  out.write('\n')

  # Print FAIL in red.
  out.write('Epic ')
  con.Colorize('FAIL', 'red')
  out.write(', my first.')

  # Print italic and bold text.
  bold = con.GetFontCode(bold=True)
  italic = con.GetFontCode(italic=True)
  normal = con.GetFontCode()
  out.write('This is {bold}bold{normal}, this is {italic}italic{normal},'
            ' and this is normal.\n'.format(bold=bold, italic=italic,
                                            normal=normal))

  # Read one character from stdin with echo disabled.
  c = con.GetRawKey()
  if c is None:
    print 'EOF\n'

  # Return the display width of a string that may contain FontCode() chars.
  display_width = con.DisplayWidth(string)

  # Reset the memoized state.
  con = console_attr.ResetConsoleAttr()

  # Print the console width and height in characters.
  width, height = con.GetTermSize()
  print 'width={width}, height={height}'.format(width=width, height=height)

  # Colorize table data cells.
  fail = console_attr.Colorizer('FAIL', 'red')
  pass = console_attr.Colorizer('PASS', 'green')
  cells = ['label', fail, 'more text', pass, 'end']
  for cell in cells;
    if isinstance(cell, console_attr.Colorizer):
      cell.Render()
    else:
      out.write(cell)
"""


import os
import sys
import unicodedata

from googlecloudsdk.core.console import console_attr_os
from googlecloudsdk.core.util import encoding as encoding_util


class BoxLineCharacters(object):
  """Box/line drawing characters.

  The element names are from ISO 8879:1986//ENTITIES Box and Line Drawing//EN:
    http://www.w3.org/2003/entities/iso8879doc/isobox.html
  """


class BoxLineCharactersUnicode(BoxLineCharacters):
  """unicode Box/line drawing characters (cp437 compatible unicode)."""
  dl = u'┐'
  dr = u'┌'
  h = u'─'
  hd = u'┬'
  hu = u'┴'
  ul = u'┘'
  ur = u'└'
  v = u'│'
  vh = u'┼'
  vl = u'┤'
  vr = u'├'
  d_dl = u'╗'
  d_dr = u'╔'
  d_h = u'═'
  d_hd = u'╦'
  d_hu = u'╩'
  d_ul = u'╝'
  d_ur = u'╚'
  d_v = u'║'
  d_vh = u'╬'
  d_vl = u'╣'
  d_vr = u'╠'


class BoxLineCharactersAscii(BoxLineCharacters):
  """ASCII Box/line drawing characters."""
  dl = u'+'
  dr = u'+'
  h = u'-'
  hd = u'+'
  hu = u'+'
  ul = u'+'
  ur = u'+'
  v = u'|'
  vh = u'+'
  vl = u'+'
  vr = u'+'
  d_dl = u'#'
  d_dr = u'#'
  d_h = u'='
  d_hd = u'#'
  d_hu = u'#'
  d_ul = u'#'
  d_ur = u'#'
  d_v = u'#'
  d_vh = u'#'
  d_vl = u'#'
  d_vr = u'#'


class ConsoleAttr(object):
  """Console attribute and special drawing characters and functions accessor.

  Use GetConsoleAttr() to get a global ConsoleAttr object shared by all callers.
  Use ConsoleAttr() for abstracting multiple consoles.

  If _out is not associated with a console, or if the console properties cannot
  be determined, the default behavior is ASCII art with no attributes.

  Attributes:
    _ANSI_COLOR: The ANSI color control sequence dict.
    _ANSI_COLOR_RESET: The ANSI color reset control sequence string.
    _csi: The ANSI Control Sequence indicator string, '' if not supported.
    _encoding: The character encoding.
        ascii: ASCII art. This is the default.
        utf8: UTF-8 unicode.
        win: Windows code page 437.
    _font_bold: The ANSI bold font embellishment code string.
    _font_italic: The ANSI italic font embellishment code string.
    _get_raw_key: A function that reads one keypress from stdin with no echo.
    _out: The console output file stream.
    _term: TERM environment variable value.
    _term_size: The terminal (x, y) dimensions in characters.
  """

  _CONSOLE_ATTR_STATE = None

  _ANSI_COLOR = {
      'red': '31;1m',
      'yellow': '33;1m',
      'green': '32m',
      'blue': '34;1m'
      }
  _ANSI_COLOR_RESET = '39;0m'

  _BULLETS_UNICODE = (u'▪', u'◆', u'▸', u'▫', u'◇', u'▹')
  _BULLETS_WINDOWS = (u'■', u'≡', u'∞', u'Φ', u'·')  # cp437 compatible unicode
  _BULLETS_ASCII = ('o', '*', '+', '-')

  def __init__(self, encoding=None, out=None):
    """Constructor.

    Args:
      encoding: Encoding override.
        ascii -- ASCII art. This is the default.
        utf8 -- UTF-8 unicode.
        win -- Windows code page 437.
      out: The console output file stream, log.out if None.
    """
    if not out:
      try:
        from googlecloudsdk.core import log  # pylint: disable=g-import-not-at-top, avoid config import loop
        out = log.out
      except ImportError:
        out = sys.stdout
    self._out = out
    # Normalize the encoding name.
    console_encoding = None
    if not encoding:
      if hasattr(self._out, 'encoding') and self._out.encoding:
        console_encoding = self._out.encoding.lower()
        if 'utf-8' in console_encoding:
          encoding = 'utf8'
        elif 'cp437' in console_encoding:
          encoding = 'cp437'
    elif encoding == 'win':
      encoding = 'cp437'
    self._encoding = encoding or 'ascii'
    self._term = os.getenv('TERM', '').lower()

    # ANSI "standard" attributes.
    if self._encoding != 'ascii' and ('screen' in self._term or
                                      'xterm' in self._term):
      # Select Graphic Rendition paramaters from
      # http://en.wikipedia.org/wiki/ANSI_escape_code#graphics
      # Italic '3' would be nice here but its not widely supported.
      self._csi = '\x1b['
      self._font_bold = '1'
      self._font_italic = '4'
    else:
      self._csi = None
      self._font_bold = ''
      self._font_italic = ''

    # Encoded character attributes.
    if self._encoding == 'utf8':
      self._box_line_characters = BoxLineCharactersUnicode()
      self._bullets = self._BULLETS_UNICODE
    elif self._encoding == 'cp437':
      self._box_line_characters = BoxLineCharactersUnicode()
      self._bullets = self._BULLETS_WINDOWS
    else:
      self._box_line_characters = BoxLineCharactersAscii()
      self._bullets = self._BULLETS_ASCII

    # OS specific attributes.
    self._get_raw_key = [console_attr_os.GetRawKeyFunction()]
    self._term_size = console_attr_os.GetTermSize()

  def Colorize(self, string, color, justify=None):
    """Writes string, optionally justified, with color to the console.

    Args:
      string: The string to write.
      color: The color name -- must b3 in _ANSI_COLOR.
      justify: The justification function, no justification if None. For
        example, justify=lambda s: s.center(10)
    """
    if justify:
      string = justify(string)
    if self._csi and color in self._ANSI_COLOR:
      self._out.write('{csi}{color_code}{string}{csi}{reset_code}'.format(
          csi=self._csi,
          color_code=self._ANSI_COLOR[color],
          reset_code=self._ANSI_COLOR_RESET,
          string=string))
      # TODO(b/35939231): Add elif self._encoding == 'cp437': code here.
    else:
      self._out.write(string)

  def ConvertOutputToUnicode(self, buf):
    """Converts a console output string buf to unicode.

    Mainly used for testing. Allows test comparisons in unicode while ensuring
    that unicode => encoding => unicode works.

    Args:
      buf: The console output string to convert.

    Returns:
      The console output string buf converted to unicode.
    """
    if isinstance(buf, unicode):
      buf = buf.encode(self._encoding)
    return unicode(buf, self._encoding, 'replace')

  def GetBoxLineCharacters(self):
    """Returns the box/line drawing characters object.

    The element names are from ISO 8879:1986//ENTITIES Box and Line Drawing//EN:
      http://www.w3.org/2003/entities/iso8879doc/isobox.html

    Returns:
      A BoxLineCharacters object for the console output device.
    """
    return self._box_line_characters

  def GetBullets(self):
    """Returns the bullet characters list.

    Use the list elements in order for best appearance in nested bullet lists,
    wrapping back to the first element for deep nesting. The list size depends
    on the console implementation.

    Returns:
      A tuple of bullet characters.
    """
    return self._bullets

  def GetControlSequenceIndicator(self):
    """Returns the control sequence indicator string.

    Returns:
      The conrol sequence indicator string or None if control sequences are not
      supported.
    """
    return self._csi

  def GetControlSequenceLen(self, buf):
    """Returns the control sequence length at the beginning of buf.

    Used in display width computations. Control sequences have display width 0.

    Args:
      buf: The string to check for a control sequence.

    Returns:
      The conrol sequence length at the beginning of buf or 0 if buf does not
      start with a control sequence.
    """
    if not self._csi or not buf.startswith(self._csi):
      return 0
    n = 0
    for c in buf:
      n += 1
      if c.isalpha():
        break
    return n

  def GetEncoding(self):
    """Returns the current encoding."""
    return self._encoding

  def GetFontCode(self, bold=False, italic=False):
    """Returns a font code string for 0 or more embellishments.

    GetFontCode() with no args returns the default font code string.

    Args:
      bold: True for bold embellishment.
      italic: True for italic embellishment.

    Returns:
      The font code string for the requested embellishments. Write this string
        to the console output to control the font settings.
    """
    if not self._csi:
      return ''
    codes = []
    if bold:
      codes.append(self._font_bold)
    if italic:
      codes.append(self._font_italic)
    return '{csi}{codes}m'.format(csi=self._csi, codes=';'.join(codes))

  def GetRawKey(self):
    """Reads one key press from stdin with no echo.

    Returns:
      The key name, None for EOF, <KEY-*> for function keys, otherwise a
      character.
    """
    return self._get_raw_key[0]()

  def GetTermSize(self):
    """Returns the terminal (x, y) dimensions in characters.

    Returns:
      (x, y): A tuple of the terminal x and y dimensions.
    """
    return self._term_size

  def DisplayWidth(self, buf):
    """Returns the display width of buf, handling unicode and ANSI controls.

    Args:
      buf: The string to count from.

    Returns:
      The display width of buf, handling unicode and ANSI controls.
    """
    if not isinstance(buf, basestring):
      # Handle non-string objects like Colorizer().
      return len(buf)
    width = 0
    i = 0
    while i < len(buf):
      if self._csi and buf[i:].startswith(self._csi):
        i += self.GetControlSequenceLen(buf[i:])
      else:
        width += GetCharacterDisplayWidth(buf[i])
        i += 1
    return width

  def SplitIntoNormalAndControl(self, buf):
    """Returns a list of (normal_string, control_sequence) tuples from buf.

    Args:
      buf: The input string containing one or more control sequences
        interspersed with normal strings.

    Returns:
      A list of (normal_string, control_sequence) tuples.
    """
    if not self._csi or not buf:
      return [(buf, '')]
    seq = []
    i = 0
    while i < len(buf):
      c = buf.find(self._csi, i)
      if c < 0:
        seq.append((buf[i:], ''))
        break
      normal = buf[i:c]
      i = c + self.GetControlSequenceLen(buf[c:])
      seq.append((normal, buf[c:i]))
    return seq

  def SplitLine(self, line, width):
    """Splits line into width length chunks.

    Args:
      line: The line to split.
      width: The width of each chunk except the last which could be smaller than
        width.

    Returns:
      A list of chunks, all but the last with display width == width.
    """
    lines = []
    chunk = ''
    w = 0
    keep = False
    for normal, control in self.SplitIntoNormalAndControl(line):
      keep = True
      while True:
        n = width - w
        w += len(normal)
        if w <= width:
          break
        lines.append(chunk + normal[:n])
        chunk = ''
        keep = False
        w = 0
        normal = normal[n:]
      chunk += normal + control
    if chunk or keep:
      lines.append(chunk)
    return lines


class Colorizer(object):
  """Resource string colorizer.

  Attributes:
    _con: ConsoleAttr object.
    _color: Color name.
    _string: The string to colorize.
    _justify: The justification function, no justification if None. For example,
      justify=lambda s: s.center(10)
  """

  def __init__(self, string, color, justify=None):
    """Constructor.

    Args:
      string: The string to colorize.
      color: Color name used to index ConsoleAttr._ANSI_COLOR.
      justify: The justification function, no justification if None. For
        example, justify=lambda s: s.center(10)
    """
    self._con = GetConsoleAttr()
    self._color = color
    self._string = string
    self._justify = justify

  def __cmp__(self, other):
    string = str(other)
    if self._string < string:
      return -1
    if self._string > string:
      return 1
    return 0

  def __len__(self):
    return self._con.DisplayWidth(self._string)

  def __str__(self):
    return self._string

  def Render(self, justify=None):
    """Renders the string as self._color on the console.

    Args:
      justify: The justification function, self._justify if None.
    """
    self._con.Colorize(self._string, self._color, justify or self._justify)


def GetConsoleAttr(encoding=None, out=None, reset=False):
  """Gets the console attribute state.

  If this is the first call or reset is True or encoding is not None and does
  not match the current encoding or out is not None and does not match the
  current out then the state is (re)initialized. Otherwise the current state
  is returned.

  This call associates the out file stream with the console. All console related
  output should go to the same stream.

  Args:
    encoding: Encoding override.
      ascii -- ASCII. This is the default.
      utf8 -- UTF-8 unicode.
      win -- Windows code page 437.
    out: The console output file stream, ConsoleAttr default if None.
    reset: Force re-initialization if True.

  Returns:
    The global ConsoleAttr state object.
  """
  attr = ConsoleAttr._CONSOLE_ATTR_STATE  # pylint: disable=protected-access
  if not reset:
    if not attr:
      reset = True
    elif encoding and encoding != attr.GetEncoding():
      reset = True
    elif out and out != attr._out:  # pylint: disable=protected-access
      reset = True
  if reset:
    attr = ConsoleAttr(encoding=encoding, out=out)
    ConsoleAttr._CONSOLE_ATTR_STATE = attr  # pylint: disable=protected-access
  return attr


def ResetConsoleAttr(encoding=None):
  """Resets the console attribute state to the console default.

  Args:
    encoding: Reset to this encoding instead of the default.
      ascii -- ASCII. This is the default.
      utf8 -- UTF-8 unicode.
      win -- Windows code page 437.

  Returns:
    The global ConsoleAttr state object.
  """
  return GetConsoleAttr(encoding=encoding, reset=True)


def GetCharacterDisplayWidth(char):
  """Returns the monospaced terminal display width of char.

  Assumptions:
    - monospaced display
    - ambiguous or unknown chars default to width 1
    - ASCII control char width is 1 => don't use this for control chars

  Args:
    char: The character to determine the display width of.

  Returns:
    The monospaced terminal display width of char: either 0, 1, or 2.
  """
  if not isinstance(char, unicode):
    # Non-unicode chars have width 1. Don't use this function on control chars.
    return 1

  # Normalize to avoid special cases.
  char = unicodedata.normalize('NFC', char)

  if unicodedata.combining(char) != 0:
    # Modifies the previous character and does not move the cursor.
    return 0
  elif unicodedata.category(char) == 'Cf':
    # Unprintable formatting char.
    return 0
  elif unicodedata.east_asian_width(char) in 'FW':
    # Fullwidth or Wide chars take 2 character positions.
    return 2
  else:
    # Don't use this function on control chars.
    return 1


def EncodeForConsole(string, encoding=None, escape=True):
  r"""Returns string encoded to prevent output codec exceptions.

  This function can be used to massage output strings that may have been encoded
  with an encoding incompatible with the standard output encoding. This happens
  frequently in tests and error messages where the string is obtained from a
  source of unknown encoding.

  Args:
    string: A string or object that has str() and unicode() methods that may
      contain an encoding incompatible with the standard output encoding.
    encoding: The output encoding name. Defaults to
      GetConsoleAttr().GetEncoding().
    escape: Replace unencodable characters with a \uXXXX or \xXX equivalent if
      True. Otherwise replace unencodable characters with an appropriate unknown
      character, '?' for ASCII, and the unicode unknown replacement character
      \uFFFE for unicode.

  Returns:
    The string encoded to avoid output codec exceptions. In the worst case,
    with escape=False, it will contain only ? characters.
  """
  try:
    # No change needed if the string encodes to ASCII.
    string.encode('ascii')
    return string
  except AttributeError:
    # The string does not have a decode method.
    try:
      string = unicode(string)
    except (TypeError, UnicodeError):
      # The string cannot be converted to unicode -- default to str() which will
      # catch objects with special __str__ methods.
      string = str(string)
  except UnicodeError:
    # The string does not encode to ASCII.
    pass

  if not encoding:
    encoding = GetConsoleAttr().GetEncoding()

  try:
    # No change needed if the string encodes to the output encoding.
    string.encode(encoding)
    return string
  except UnicodeError:
    # the string does not encode to the output encoding.
    pass

  try:
    # The string is encoded using the standard output encoding. Decoding here
    # gets the string in a form that will print to the standard output.
    return string.decode(encoding)
  except (AttributeError, UnicodeError):
    # Unknown encoding.
    string = DecodeFromConsole(string, encoding=encoding)

    try:
      # No change needed if the string encodes to the output encoding.
      string.encode(encoding)
      return string
    except UnicodeError:
      # Give up and return a string with unknown characters replaced by ?
      # (escape=False) or a C-style escape (escape=True).
      return string.encode(encoding,
                           'backslashreplace' if escape else 'replace')


def DecodeFromConsole(string, encoding=None):
  """Returns string with non-ascii characters decoded.

  Args:
    string: A string or object that has str() and unicode() methods that may
      contain an encoding incompatible with the standard output encoding.
    encoding: The encoding to decode. Defaults to
      GetConsoleAttr().GetEncoding().

  Returns:
    The string with non-ascii characters decoded. If the input string is
    ascii then it is returned unchanged, otherwise the decoded unicode string
    is returned.
  """
  if not encoding:
    encoding = GetConsoleAttr().GetEncoding()
  return encoding_util.Decode(string, encoding=encoding)
