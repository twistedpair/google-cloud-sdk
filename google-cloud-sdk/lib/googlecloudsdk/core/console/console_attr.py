# -*- coding: utf-8 -*- #

# Copyright 2015 Google Inc. All Rights Reserved.

"""A module for console attributes, special characters and functions.

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
  c = con.GetRawChar()
  if c is None:
    print 'EOF\n'

  # Return the print width of a string that may contain FontCode() chars.
  print_width = con.PrintWidth(string)

  # Reset the memoized state.
  con = console_attr.GetConsoleAttr(reset=True)

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

from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_attr_os


class BoxLineCharacters(object):
  """Box/line drawing characters.

  The element names are from ISO 8879:1986//ENTITIES Box and Line Drawing//EN:
    http://www.w3.org/2003/entities/iso8879doc/isobox.html
  """


class BoxLineCharactersUtf8(BoxLineCharacters):
  """UTF-8 Box/line drawing characters."""
  dl = '┐'
  dr = '┌'
  h = '─'
  hd = '┬'
  hu = '┴'
  ul = '┘'
  ur = '└'
  v = '│'
  vh = '┼'
  vl = '┤'
  vr = '├'
  d_dl = '╗'
  d_dr = '╔'
  d_h = '═'
  d_hd = '╦'
  d_hu = '╩'
  d_ul = '╝'
  d_ur = '╚'
  d_v = '║'
  d_vh = '╬'
  d_vl = '╣'
  d_vr = '╠'


class BoxLineCharactersWindows(BoxLineCharacters):
  """UTF-8 Box/line drawing characters."""
  dl = '\xBF'
  dr = '\xDA'
  h = '\xC4'
  hd = '\xC2'
  hu = '\xC1'
  ul = '\xD9'
  ur = '\xC0'
  v = '\xB3'
  vh = '\xC5'
  vl = '\xB4'
  vr = '\xC3'
  d_dl = '\xBB'
  d_dr = '\xC9'
  d_h = '\xCD'
  d_hd = '\xCB'
  d_hu = '\xCA'
  d_ul = '\xBC'
  d_ur = '\xC8'
  d_v = '\xBA'
  d_vh = '\xCE'
  d_vl = '\xB9'
  d_vr = '\xCC'


class BoxLineCharactersAscii(BoxLineCharacters):
  """ASCII Box/line drawing characters."""
  dl = '+'
  dr = '+'
  h = '-'
  hd = '+'
  hu = '+'
  ul = '+'
  ur = '+'
  v = '|'
  vh = '+'
  vl = '+'
  vr = '+'
  d_dl = '#'
  d_dr = '#'
  d_h = '='
  d_hd = '#'
  d_hu = '#'
  d_ul = '#'
  d_ur = '#'
  d_v = '#'
  d_vh = '#'
  d_vl = '#'
  d_vr = '#'


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
    _get_raw_char: A function that reads one character from stdin with no echo.
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

  _BULLETS_UTF8 = ('●', '■', '◆', '○', '□', '◇')
  _BULLETS_WINDOWS = ('\x07', '\xFE', '\x04')
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
    self._out = out or log.out
    # Normalize the encoding name.
    if not encoding:
      encoding = 'ascii'
      if hasattr(self._out, 'encoding') and self._out.encoding:
        console_encoding = self._out.encoding.lower()
        if 'utf-8' in console_encoding:
          encoding = 'utf8'
        elif 'cp437' in console_encoding:
          encoding = 'win'
    self._encoding = encoding
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
      self._box_line_characters = BoxLineCharactersUtf8()
      self._bullets = self._BULLETS_UTF8
    elif self._encoding == 'win':
      self._box_line_characters = BoxLineCharactersWindows()
      self._bullets = self._BULLETS_WINDOWS
    else:
      self._box_line_characters = BoxLineCharactersAscii()
      self._bullets = self._BULLETS_ASCII

    # OS specific attributes.
    self._get_raw_char = [console_attr_os.GetRawCharFunction()]
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
      # TODO(gsfowler): Add elif self._encoding == 'win': code here.
    else:
      self._out.write(string)

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

    Used in print width computations. Control sequences have print width 0.

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

  def GetRawChar(self):
    """Reads one character from stdin with no echo.

    Returns:
      One raw character.
    """
    return self._get_raw_char[0]()

  def GetTermSize(self):
    """Returns the terminal (x, y) dimensions in characters.

    Returns:
      (x, y): A tuple of the terminal x and y dimensions.
    """
    return self._term_size

  def PrintWidth(self, buf):
    """Returns the print width of buf which may contain ANSI control sequences.

    Args:
      buf: The string to count from.

    Returns:
      The print width of buf.
    """
    if not self._csi:
      return len(buf)
    width = 0
    i = 0
    while i < len(buf):
      csi_index = buf.find(self._csi, i)
      if csi_index < 0:
        width += len(buf) - i
        break
      width += csi_index - i
      i = csi_index + self.GetControlSequenceLen(buf[csi_index:])
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
      A list of chunks, all but the last with print width == width.
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
    return len(self._string)

  def __str__(self):
    return self._string

  def Render(self, justify=None):
    """Renders the string as self._color on the console.

    Args:
      justify: The justification function, self._justify if None.
    """
    self._con.Colorize(self._string, self._color, justify or self._justify)


def GetConsoleAttr(encoding=None, out=None, reset=False):
  """Get the console attribute state.

  If this is the first call or reset is True or encoding is not None and does
  not match the current encoding or out is not None and does not match the
  current out then the state is (re)initialized. Otherwise the current state
  is returned.

  This call associates the out file stream with the console. All console related
  output should go to the same stream.

  Args:
    encoding: Encoding override.
      ascii -- ASCII art. This is the default.
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
