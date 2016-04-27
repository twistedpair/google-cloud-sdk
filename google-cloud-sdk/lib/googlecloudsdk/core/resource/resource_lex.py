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

r"""Resource expression lexer.

This class is used to parse resource keys, quoted tokens, and operator strings
and characters from resource filter and projection expression strings. Tokens
are defined by isspace() and caller specified per-token terminator characters.
" or ' quotes are supported, with these literal escapes: \\ => \, \' => ',
\" => ", and \<any-other-character> => \<any-other-character>.

Typical resource usage:

  # Initialize a lexer with the expression string.
  lex = resource_lex.Lexer(expression_string)
  # isspace() separated tokens. lex.SkipSpace() returns False at end of input.
  while lex.SkipSpace():
    # Save the expression string position for syntax error annotation.
    here = lex.GetPosition()
    # The next token must be a key.
    key = lex.Key()
    if not key:
      if lex.EndOfInput():
        # End of input is OK here.
        break
      # There were some characters in the input that did not form a valid key.
      raise resource_exceptions.ExpressionSyntaxError(
          'key expected [{0}].'.format(lex.Annotate(here)))
    # Check if the key is a function call.
    if lex.IsCharacter('('):
      # Collect the actual args and convert numeric args to float or int.
      args = lex.Args(convert=True)
    else:
      args = None
    # Skip an isspace() characters. End of input will fail with an
    # 'Operator expected [...]' resource_exceptions.ExpressionSyntaxError.
    lex.SkipSpace(token='Operator')
    # The next token must be one of these operators ...
    operator = lex.IsCharacter('+-*/&|')
    if not operator:
      # ... one of the operator names.
      if lex.IsString('AND'):
        operator = '&'
      elif lex.IsString('OR'):
        operator = '|'
      else:
        raise resource_exceptions.ExpressionSyntaxError(
            'Operator expected [{0}].'.format(lex.Annotate()))
    # The next token must be an operand. Convert to float or int if possible.
    # lex.Token() by default eats leading isspace().
    operand = lex.Token(convert=True)
    if not operand:
      raise resource_exceptions.ExpressionSyntaxErrorSyntaxError(
          'Operand expected [{0}].'.format(lex.Annotate()))
    # Process the key, args, operator and operand.
    Process(key, args, operator, operand)
"""

import re

from googlecloudsdk.core.resource import resource_exceptions


# Reserved operator characters. Resource keys cannot contain unquoted operator
# characters. This prevents key/operator clashes in expressions.
_RESERVED_OPERATOR_CHARS = '[].(){},:=!<>+*/%&|^~@#;?'


class Lexer(object):
  """Resource expression lexer.

  This lexer handles simple and compound tokens. Compound tokens returned by
  Key() and Args() below are not strictly lexical items (i.e., they are parsed
  against simple grammars), but treating them as tokens here simplifies the
  resource expression parsers that use this class and avoids code replication.

  Attributes:
    _ESCAPE: The quote escape character.
    _QUOTES: The quote characters.
    _expr: The expression string.
    _position: The index of the next character in _expr to parse.
    _aliases: Parsed key alias dict indexed by the first key name.
  """
  _ESCAPE = '\\'
  _QUOTES = '\'"'

  def __init__(self, expression, aliases=None):
    """Initializes a resource lexer.

    Args:
      expression: The expression string.
      aliases: Parsed key alias dict indexed by the first key name.
    """
    self._expr = expression or ''
    self._position = 0
    # There is a subtle difference betwee None and {} here.
    # If aliases is {} then it is a dict to add more aliases to.
    # If aliases is None then use a local dict and discard it when done.
    self._aliases = {} if aliases is None else aliases

  def EndOfInput(self, position=None):
    """Checks if the current expression string position is at the end of input.

    Args:
      position: Checks position instead of the current expression position.

    Returns:
      True if the expression string position is at the end of input.
    """
    if position is None:
      position = self._position
    return position >= len(self._expr)

  def GetPosition(self):
    """Returns the current expression position.

    Returns:
      The current expression position.
    """
    return self._position

  def SetPosition(self, position):
    """Sets the current expression position.

    Args:
      position: Sets the current position to position. Position should be 0 or a
        previous value returned by GetPosition().
    """
    self._position = position

  def Annotate(self, position=None):
    """Returns the expression string annotated for syntax error messages.

    The current position is marked by '*HERE*' for visual effect.

    Args:
      position: Uses position instead of the current expression position.

    Returns:
      The expression string with current position annotated.
    """
    here = position if position is not None else self._position
    cursor = '*HERE*'  # For visual effect only.
    if here > 0 and not self._expr[here - 1].isspace():
      cursor = ' ' + cursor
    if here < len(self._expr) and not self._expr[here].isspace():
      cursor += ' '
    return '{0}{1}{2}'.format(self._expr[0:here], cursor, self._expr[here:])

  def SkipSpace(self, token=None):
    """Skips spaces in the expression string.

    Args:
      token: The expected next token description string, None if end of input is
        OK. This string is used in the exception message. It is not used to
        validate the type of the next token.

    Raises:
      ExpressionSyntaxError: End of input reached after skipping and a token is
        expected.

    Returns:
      True if the expression is not at end of input.
    """
    while not self.EndOfInput():
      if not self._expr[self._position].isspace():
        return True
      self._position += 1
    if token:
      raise resource_exceptions.ExpressionSyntaxError(
          '{0} expected [{1}].'.format(token, self.Annotate()))
    return False

  def IsCharacter(self, characters, peek=False, eoi_ok=False):
    """Checks if the next character is in characters and consumes it if it is.

    Args:
      characters: A set of characters to check for. It may be a string, tuple,
        list or set.
      peek: Does not consume a matching character if True.
      eoi_ok: True if end of input is OK. Returns None if at end of input.

    Raises:
      ExpressionSyntaxError: End of input reached and peek and eoi_ok are False.

    Returns:
      The matching character or None if no match.
    """
    if self.EndOfInput():
      if peek or eoi_ok:
        return None
      raise resource_exceptions.ExpressionSyntaxError(
          'More tokens expected [{0}].'.format(self.Annotate()))
    c = self._expr[self._position]
    if c not in characters:
      return None
    if not peek:
      self._position += 1
    return c

  def IsString(self, name, peek=False):
    """Skips leading space and checks if the next token is name.

    One of space, '(', or end of input terminates the next token.

    Args:
      name: The token name to check.
      peek: Does not consume the string on match if True.

    Returns:
      True if the next space or ( separated token is name.
    """
    if not self.SkipSpace():
      return False
    i = self.GetPosition()
    if not self._expr[i:].startswith(name):
      return False
    i += len(name)
    if self.EndOfInput(i) or self._expr[i].isspace() or self._expr[i] == '(':
      if not peek:
        self.SetPosition(i)
      return True
    return False

  def Token(self, terminators='', space=True, convert=False):
    """Parses a possibly quoted token from the current expression position.

    The quote characters are in _QUOTES. The _ESCAPE character can prefix
    an _ESCAPE or _QUOTE character to treat it as a normal character. If
    _ESCAPE is at end of input, or is followed by any other character, then it
    is treated as a normal character.

    Quotes may be adjacent ("foo"" & ""bar" => "foo & bar") and they may appear
    mid token (foo" & "bar => "foo & bar").

    Args:
      terminators: A set of characters that terminate the token. isspace()
        characters always terminate the token. It may be a string, tuple, list
          or set.
      space: True if space characters should be skipped after the token. Space
        characters are always skipped before the token.
      convert: Converts unquoted numeric string tokens to numbers if True.

    Raises:
      ExpressionSyntaxError: The expression has a syntax error.

    Returns:
      None if there is no token, the token string if convert is False or the
      token is quoted, otherwise the converted float / int / string value of
      the token.
    """
    quote = None  # The current quote character, None if not in quote.
    quoted = False  # True if the token is constructed from quoted parts.
    token = None  # The token char list, None for no token, [] for empty token.
    i = self.GetPosition()
    while not self.EndOfInput(i):
      c = self._expr[i]
      if c == self._ESCAPE and not self.EndOfInput(i + 1):
        # Only _ESCAPE, the current quote or _QUOTES are escaped.
        c = self._expr[i + 1]
        if token is None:
          token = []
        if (c != self._ESCAPE and c != quote and
            (quote or c not in self._QUOTES)):
          token.append(self._ESCAPE)
        token.append(c)
        i += 1
      elif c == quote:
        # The end of the current quote.
        quote = None
      elif not quote and c in self._QUOTES:
        # The start of a new quote.
        quote = c
        quoted = True
        if token is None:
          token = []
      elif not quote and c in terminators:
        # Only unquoted terminators terminate the token.
        break
      elif quote or not c.isspace():
        # Append c to the token string.
        if token is None:
          token = []
        token.append(c)
      elif token is not None:
        # A space after any token characters is a terminator.
        break
      i += 1
    if quote:
      raise resource_exceptions.ExpressionSyntaxError(
          'Unterminated [{0}] quote [{1}].'.format(quote, self.Annotate()))
    self.SetPosition(i)
    if space:
      self.SkipSpace()
    if token is not None:
      # Convert the list of token chars to a string.
      token = ''.join(token)
    if convert and token and not quoted:
      # Only unquoted tokens are converted.
      try:
        return int(token)
      except ValueError:
        try:
          return float(token)
        except ValueError:
          pass
    return token

  def Args(self, convert=False):
    """Parses a ,-separated, )-terminated arg list.

    The initial '(' has already been consumed by the caller. The arg list may
    be empty. Otherwise the first ',' must be preceded by a non-empty argument,
    and every ',' must be followed by a non-empty argument.

    Args:
      convert: Converts unquoted numeric string args to numbers if True.

    Raises:
      ExpressionSyntaxError: The expression has a syntax error.

    Returns:
      [...]: The arg list.
    """
    required = False  # True if there must be another argument token.
    args = []
    while True:
      here = self.GetPosition()
      arg = self.Token(',)', convert=convert)
      end = self.IsCharacter(')')
      if arg is not None:
        args.append(arg)
      elif required or not end:
        raise resource_exceptions.ExpressionSyntaxError(
            'Argument expected [{0}].'.format(self.Annotate(here)))
      if end:
        break
      if not self.IsCharacter(','):
        raise resource_exceptions.ExpressionSyntaxError(
            'Closing ) expected in argument list [{0}].'.format(
                self.Annotate(here)))
      required = True
    return args

  def Key(self):
    """Parses a resource key from the expression.

    A resource key is a '.' separated list of names with optional [] slice or
    [NUMBER] array indices. A parsed key is encoded as an ordered list of
    tokens, where each token may be:

      KEY VALUE   PARSED VALUE  DESCRIPTION
      ---------   ------------  -----------
      name        string        A dotted name list element.
      [NUMBER]    NUMBER        An array index.
      []          None          An array slice.

    For example, the key 'abc.def[123].ghi[].jkl' parses to this encoded list:
      ['abc', 'def', 123, 'ghi', None, 'jkl']

    Raises:
      ExpressionSyntaxError: The expression has a syntax error.

    Returns:
      The parsed key which is a list of string, int and/or None elements.
    """
    key = []
    while not self.EndOfInput():
      here = self.GetPosition()
      name = self.Token(_RESERVED_OPERATOR_CHARS, space=False)
      if name:
        is_not_function = not self.IsCharacter('(', peek=True, eoi_ok=True)
        if not key and is_not_function and name in self._aliases:
          key.extend(self._aliases[name])
        else:
          key.append(name)
      elif not self.IsCharacter('[', peek=True):
        # A single . is a valid key that names the top level resource.
        if (not key and self.IsCharacter('.') and (
            self.EndOfInput() or self.IsCharacter(
                _RESERVED_OPERATOR_CHARS, peek=True, eoi_ok=True))):
          break
        raise resource_exceptions.ExpressionSyntaxError(
            'Non-empty key name expected [{0}].'.format(self.Annotate(here)))
      if self.EndOfInput():
        break
      if self.IsCharacter(']'):
        raise resource_exceptions.ExpressionSyntaxError(
            'Unmatched ] in key [{0}].'.format(self.Annotate(here)))
      while self.IsCharacter('[', eoi_ok=True):
        # [] slice or [NUMBER] array index.
        index = self.Token(']', convert=True)
        self.IsCharacter(']')
        key.append(index)
      if not self.IsCharacter('.', eoi_ok=True):
        break
      if self.EndOfInput():
        # Dangling '.' is not allowed.
        raise resource_exceptions.ExpressionSyntaxError(
            'Non-empty key name expected [{0}].'.format(self.Annotate()))
    return key


def GetKeyName(key):
  """Returns the string representation for a parsed key.

  This is the inverse of Lex.Key().

  Args:
    key: A parsed key, which is an ordered list of key names/indices. Each
      element in the list may be one of:
        str - A resource property name. This could be a class attribute name or
          a dict index.
        int - A list index. Selects one member is the list. Negative indices
          count from the end of the list, starting with -1 for the last element
          in the list. An out of bounds index is not an error; it produces the
          value None.
        None - A list slice. Selects all members of a list or dict like object.
          A slice of an empty dict or list is an empty dict or list.

  Returns:
    The string representation of the parsed key.
  """
  parts = []
  for part in key:
    if part is None:
      part = '[]'
      if parts:
        parts[-1] += part
        continue
    elif isinstance(part, (int, long)):
      part = '[{part}]'.format(part=part)
      if parts:
        parts[-1] += part
        continue
    elif re.search(r'\W', part):
      part = part.replace('\\', '\\\\')
      part = part.replace('"', '\\"')
      part = u'"{part}"'.format(part=part)
    parts.append(part)
  return '.'.join(parts) if parts else '.'
