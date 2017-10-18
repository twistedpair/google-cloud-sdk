# Copyright 2017 Google Inc. All Rights Reserved.
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

"""A basic command line parser.

This command line parser does the bare minimum required to understand the
commands and flags being used as well as perform completion. This is not a
replacement for argparse (yet).
"""

from __future__ import unicode_literals

import enum

from googlecloudsdk.calliope import cli_tree
from googlecloudsdk.command_lib.shell import lexer


LOOKUP_COMMANDS = cli_tree.LOOKUP_COMMANDS
LOOKUP_CHOICES = cli_tree.LOOKUP_CHOICES
LOOKUP_COMPLETER = cli_tree.LOOKUP_COMPLETER
LOOKUP_FLAGS = cli_tree.LOOKUP_FLAGS
LOOKUP_GROUPS = cli_tree.LOOKUP_GROUPS
LOOKUP_IS_HIDDEN = cli_tree.LOOKUP_IS_HIDDEN
LOOKUP_NAME = cli_tree.LOOKUP_NAME
LOOKUP_NARGS = cli_tree.LOOKUP_NARGS
LOOKUP_POSITIONALS = cli_tree.LOOKUP_POSITIONALS
LOOKUP_TYPE = cli_tree.LOOKUP_TYPE

LOOKUP_CLI_VERSION = cli_tree.LOOKUP_CLI_VERSION


class ArgTokenType(enum.Enum):
  UNKNOWN = 0
  GROUP = 1
  COMMAND = 2
  FLAG = 3
  FLAG_ARG = 4
  POSITIONAL = 5


class ArgToken(object):
  """Shell token info.

  Attributes:
    value: A string associated with the token.
    token_type: Instance of ArgTokenType
    tree: A subtree of CLI root.
    start: The index of the first char in the original string.
    end: The index directly after the last char in the original string.
  """

  def __init__(self, value, token_type, tree, start=None, end=None):
    self.value = value
    self.token_type = token_type
    self.tree = tree
    self.start = start
    self.end = end

  def __eq__(self, other):
    """Equality based on properties."""
    if isinstance(other, self.__class__):
      return self.__dict__ == other.__dict__
    return False

  def __repr__(self):
    """Improve debugging during tests."""
    return 'ArgToken({}, {}, {}, {})'.format(self.value, self.token_type,
                                             self.start, self.end)


def ParseCommand(root, line):
  """Parses the next command from line and returns a list of ArgTokens.

  The caller can examine the return value to determine the parts of the line
  that were ignored and the remainder of the line that was not lexed/parsed yet.

  Args:
    root: The CLI tree root.
    line: a string containing a command line

  Returns:
    A list of ArgTokens.
  """
  return ParseArgs(root, lexer.GetShellTokens(line))


def ParseArgs(root, tokens):
  """Parses a list of lexer.ShellTokens as a command.

  The parse stops at the first token that is not an ARG or FLAG. That token is
  not consumed.

  Args:
    root: The CLI tree root.
    tokens: list of lexer.ShellTokens, consumed from the left

  Returns:
    A list of ArgTokens.
  """
  cmd = root
  positionals_seen = 0
  positional = None
  positional_nargs = None

  args = []

  while tokens:
    token = tokens[0]
    value = token.UnquotedValue()

    if token.lex == lexer.ShellTokenType.FLAG:
      ParseFlag(cmd, tokens, args)

    elif token.lex == lexer.ShellTokenType.ARG:
      tokens.pop(0)
      if value in cmd[LOOKUP_COMMANDS]:
        cmd = cmd[LOOKUP_COMMANDS][value]

        if cmd[LOOKUP_COMMANDS]:
          token_type = ArgTokenType.GROUP
        else:
          token_type = ArgTokenType.COMMAND

        args.append(ArgToken(value, token_type, cmd, token.start, token.end))

      elif positional_nargs in ('*', '+'):
        args.append(ArgToken(
            value, ArgTokenType.POSITIONAL, positional, token.start, token.end))

      elif len(cmd[LOOKUP_POSITIONALS]) > positionals_seen:
        positional = cmd[LOOKUP_POSITIONALS][positionals_seen]
        positional_nargs = positional[LOOKUP_NARGS]
        args.append(ArgToken(
            value, ArgTokenType.POSITIONAL, positional, token.start, token.end))
        positionals_seen += 1

      else:
        args.append(ArgToken(
            value, ArgTokenType.UNKNOWN, cmd, token.start, token.end))
    else:
      break

  return args


def ParseFlag(cmd, tokens, args):
  """Parse a list of lexer.ShellTokens as a flag and append to args.

  Args:
    cmd: the current location in the CLI root
    tokens: list of lexer.ShellTokens of type ARG or FLAG where the first is
      FLAG. This list is popped from the left as tokens are consumed.
    args: An ArgToken list to append flag tokens to
  """

  token = tokens.pop(0)
  arg = token.UnquotedValue()
  name = arg
  value = None

  name_start = token.start
  name_end = token.end
  value_start = None
  value_end = None

  if '=' in name:
    # inline flag value
    name, value = arg.split('=', 1)
    name_end = name_start + len(name)
    value_start = name_end + 1
    value_end = value_start + len(value)

  flag = cmd[LOOKUP_FLAGS].get(name)
  if not flag or flag[LOOKUP_IS_HIDDEN]:
    args.append(
        ArgToken(arg, ArgTokenType.UNKNOWN, cmd, token.start, token.end))
    return

  if flag[LOOKUP_TYPE] != 'bool' and value is None and tokens:
    # next arg is the flag value
    token = tokens.pop(0)
    value = token.UnquotedValue()
    value_start = token.start
    value_end = token.end

  args.append(
      ArgToken(name, ArgTokenType.FLAG, flag, name_start, name_end))
  if value is not None:
    args.append(
        ArgToken(value, ArgTokenType.FLAG_ARG, None, value_start, value_end))
