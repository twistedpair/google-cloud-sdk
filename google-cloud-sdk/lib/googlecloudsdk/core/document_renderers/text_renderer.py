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

"""Cloud SDK markdown document text renderer."""

from googlecloudsdk.core.console import console_attr
from googlecloudsdk.core.document_renderers import renderer


class TextRenderer(renderer.Renderer):
  """Renders markdown to text.

  Attributes:
    _BULLET_DEDENT: Nested bullet indentation adjustment in characters.
    _INDENT: Indentation increment in characters for each level.
    _attr: console_attr.ConsoleAttr object.
    _bullet: List of bullet characters indexed by list level modulo #bullets.
    _blank: True if the output already contains a blank line. Used to avoid
      sequences of 2 or more blank lines in the output.
    _csi_char: The first control sequence indicator character or None if control
      sequences are not supported.
    _fill: The number of characters in the current output line.
    _ignore_width: True if the next output word should ignore _width.
    _indent: List of left indentations in characters indexed by _level.
    _level: The section or list level counting from 0.
    _table: True if currently rendering a table.
  """
  _BULLET_DEDENT = 2
  _INDENT = 4
  _SPLIT_INDENT = 2

  def __init__(self, *args, **kwargs):
    super(TextRenderer, self).__init__(*args, **kwargs)
    # We want the rendering to match the default console encoding. self._out
    # could be a file or pipe to a pager, either way we still want to see rich
    # encoding if the console supports it.
    encoding = console_attr.GetConsoleAttr().GetEncoding()
    self._attr = console_attr.GetConsoleAttr(out=self._out, encoding=encoding)
    self._blank = True
    self._bullet = self._attr.GetBullets()
    self._csi_char = self._attr.GetControlSequenceIndicator()
    if self._csi_char:
      self._csi_char = self._csi_char[0]
    self._fill = 0
    self._ignore_width = False
    self._indent = [self._INDENT]
    self._level = 0
    self._table = False

  def _Flush(self):
    """Flushes the current collection of Fill() lines."""
    self._ignore_width = False
    if self._fill:
      self._out.write('\n')
      self._blank = False
      self._fill = 0

  def _SetIndentation(self, level, bullet=False):
    """Sets the indentation level and character offset.

    Args:
      level: The desired indentaton level.
      bullet: True if indentation is for a bullet list.
    """
    if self._level < level:
      # Level increases are strictly 1 at a time.
      if level >= len(self._indent):
        self._indent.append(0)
      indent = self._INDENT
      if bullet and level > 1:
        # Nested bullet indentation is less than normal indent for aesthetics.
        indent -= self._BULLET_DEDENT
      self._indent[level] = self._indent[level - 1] + indent
    self._level = level

  def Example(self, line):
    """Displays line as an indented example.

    Args:
      line: The example line text.
    """
    self._fill = self._indent[self._level] + self._INDENT
    self._out.write(' ' * self._fill + line + '\n')
    self._blank = False
    self._fill = 0

  def Fill(self, line):
    """Adds a line to the output, splitting to stay within the output width.

    This is close to textwrap.wrap() except that control sequence characters
    don't count in the width computation.

    Args:
      line: The text line.
    """
    self._blank = True
    for word in line.split():
      if not self._fill:
        self._fill = self._indent[self._level] - 1
        self._out.write(' ' * self._fill)
      width = self._attr.DisplayWidth(word)
      if self._fill + width + 1 >= self._width and not self._ignore_width:
        self._out.write('\n')
        self._fill = self._indent[self._level]
        self._out.write(' ' * self._fill)
      else:
        self._ignore_width = False
        if self._fill:
          self._fill += 1
          self._out.write(' ')
      self._fill += width
      self._out.write(word)

  def Finish(self):
    """Finishes all output document rendering."""
    self._Flush()
    self.Font(out=self._out)

  def Font(self, attr=None, out=None):
    """Returns the font embellishment string for attr.

    Args:
      attr: None to reset to the default font, otherwise one of renderer.BOLD,
        renderer.ITALIC, or renderer.CODE.
      out: Writes tags to this stream if not None.

    Returns:
      The font embellishment string.
    """
    if attr is None:
      self._font = 0
    else:
      mask = 1 << attr
      self._font ^= mask
    code = self._attr.GetFontCode(self._font & (1 << renderer.BOLD),
                                  self._font & (1 << renderer.ITALIC))
    if out:
      out.write(code)
    return code

  def Heading(self, level, heading):
    """Renders a heading.

    Args:
      level: The heading level counting from 1.
      heading: The heading text.
    """
    if level == 1 and heading.endswith('(1)'):
      # Ignore man page TH.
      return
    self._Flush()
    self.Font(out=self._out)
    if level > 2:
      self._out.write('  ' * (level - 2))
    self._out.write(self.Font(renderer.BOLD) + heading +
                    self.Font(renderer.BOLD) + '\n')
    if level == 1:
      self._out.write('\n')
    self._blank = True
    self._level = 0
    self._rows = []

  def Line(self):
    """Renders a paragraph separating line."""
    self._Flush()
    if not self._blank:
      self._blank = True
      self._out.write('\n')

  def List(self, level, definition=None):
    """Renders a bullet or definition list item.

    Args:
      level: The list nesting level, 0 if not currently in a list.
      definition: Definition list text if not None, bullet list otherwise.
    """
    self._Flush()
    if not level:
      self._level = level
    elif definition:
      self._SetIndentation(level)
      self._out.write(' ' * (self._indent[level] - self._INDENT + 1) +
                      definition + '\n')
    else:
      self._SetIndentation(level, bullet=True)
      self._out.write(' ' * (self._indent[level] - self._BULLET_DEDENT) +
                      self._bullet[(level - 1) % len(self._bullet)])
      self._fill = self._indent[level] + 1
      self._ignore_width = True

  def Synopsis(self, line):
    """Renders NAME and SYNOPSIS lines as a hanging indent.

    Collapses adjacent spaces to one space, deletes trailing space, and doesn't
    split top-level nested [...] groups. Also detects and does not count
    terminal control sequences.

    Args:
      line: The NAME or SYNOPSIS text.
    """
    def SkipSpace(line, index):
      """Skip space characters starting at line[index].

      Args:
        line: The string.
        index: The starting index in string.

      Returns:
        The index in line after spaces or len(line) at end of string.
      """
      while index < len(line):
        c = line[index]
        if c != ' ':
          break
        index += 1
      return index

    def SkipControlSequence(line, index):
      """Skip the control sequence at line[index].

      Args:
        line: The string.
        index: The starting index in string.

      Returns:
        The index in line after the control sequence or len(line) at end of
        string.
      """
      n = self._attr.GetControlSequenceLen(line[index:])
      if not n:
        n = 1
      return index + n

    def SkipNest(line, index, open_char='[', close_char=']'):
      """Skip a [...] nested bracket group starting at line[index].

      Args:
        line: The string.
        index: The starting index in string.
        open_char: The open nesting character.
        close_char: The close nesting character.

      Returns:
        The index in line after the nesting group or len(line) at end of string.
      """
      nest = 0
      while index < len(line):
        c = line[index]
        index += 1
        if c == open_char:
          nest += 1
        elif c == close_char:
          nest -= 1
          if nest <= 0:
            break
        elif c == self._csi_char:
          index = SkipControlSequence(line, index)
      return index

    # Split the line into token, token | token, and [...] groups.
    groups = []
    i = SkipSpace(line, 0)
    beg = i
    while i < len(line):
      c = line[i]
      if c == ' ':
        end = i
        i = SkipSpace(line, i)
        if i <= (len(line) - 1) and line[i] == '|' and line[i + 1] == ' ':
          i = SkipSpace(line, i + 1)
        else:
          groups.append(line[beg:end])
          beg = i
      elif c == '[':
        i = SkipNest(line, i)
      elif c == self._csi_char:
        i = SkipControlSequence(line, i)
      else:
        i += 1
    if beg < len(line):
      groups.append(line[beg:])

    # Output the groups.
    indent = self._indent[0] - 1
    running_width = indent
    self._out.write(' ' * running_width)
    indent += self._INDENT
    for group in groups:
      w = self._attr.DisplayWidth(group) + 1
      if (running_width + w) >= self._width:
        running_width = indent
        self._out.write('\n' + ' ' * running_width)
        if (running_width + w) >= self._width:
          # This group is wider than the max width and must be split into parts.
          sep = ' '
          for part in group.split(' | '):
            w = self._attr.DisplayWidth(part)
            if sep != ' ' and (running_width + len(sep) + w) >= self._width:
              running_width = indent + self._SPLIT_INDENT
              self._out.write('\n' + ' ' * running_width)
            self._out.write(sep + part)
            running_width += len(sep) + w
            sep = ' | '
          continue
      self._out.write(' ' + group)
      running_width += w
    self._out.write('\n\n')

  def Table(self, line):
    """Renders a table line.

    Nested tables are not supported. The first call on a new table is:
      Table(attributes)
    the intermediate calls add the heading and data lines and the last call is:
      Table(None)

    Args:
      line: A CSV table data line.
    """
    if line is None:
      # TODO(user): Use resource_printer.TablePrinter() when it lands.
      if self._rows:
        cols = len(self._rows[0])
        width = [0 for _ in range(cols)]
        for row in self._rows:
          for i in range(cols - 1):
            w = len(row[i])
            if width[i] <= w:
              width[i] = w + 1
        for row in self._rows:
          self._out.write(' ' * (self._indent[self._level] + 2))
          for i in range(cols - 1):
            self._out.write(row[i].ljust(width[i]))
          self._out.write(row[-1] + '\n')
        self._rows = []
      self._table = False
      self._out.write('\n')
    elif not self._table:
      self._table = True
      self.Line()
    else:
      self._rows.append(line.split(','))
