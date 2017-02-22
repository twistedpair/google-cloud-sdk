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
"""A basic gcloud argument parser.

  This gcloud parser does the bare minimum required to understand the commands
  and flags being used as well as perform completion. This is not a replacement
  for argparse (yet).
"""

from __future__ import unicode_literals

import enum

from googlecloudsdk.command_lib.shell import shell_lexer as lexer
from googlecloudsdk.command_lib.shell.gcloud_tree import gcloud_tree


class GcloudInvocation(object):
  """An invocation of gcloud.

  Attributes:
    tokens: the ArgTokens that make up the invocation
    command: the COMMAND token (if any)
    groups: a list of the GROUP tokens
    flags: a list of the FLAG tokens
    positionals: a list of the POSITIONAL tokens
  """

  def __init__(self, tokens):
    self.tokens = tokens
    self.command = None
    self.groups = []
    self.flags = []
    self.positionals = []

    for token in tokens:
      if token.token_type == ArgTokenType.COMMAND:
        self.command = token
      elif token.token_type == ArgTokenType.GROUP:
        self.groups.append(token)
      elif token.token_type == ArgTokenType.FLAG:
        self.flags.append(token)
      elif token.token_type == ArgTokenType.POSITIONAL:
        self.positionals.append(token)

  def GetCommandOrGroup(self):
    """Get the command or last group."""
    if self.command is not None:
      return self.command

    if self.groups:
      return self.groups[-1]

    return None


class ArgTokenType(enum.Enum):
  UNKNOWN = 0
  GROUP = 1
  COMMAND = 2
  FLAG = 3
  POSITIONAL = 4


class ArgToken(object):
  """Shell token info.

  Attributes:
    value: A string associated with the token.
    token_type: Instance of ArgTokenType
    tree: A subtree of googlecloudsdk.command_lib.shell.gcloud_tree.gcloud_tree
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


def ParseLine(line):
  """Parse a gcloud command line.

  Args:
    line: a string containing a gcloud command

  Returns:
    A list of ArgTokens.
  """
  sh_tokens = lexer.GetShellTokens(line)
  if not sh_tokens:
    return []

  # Cut off at first non-arg token
  i = 0
  while i < len(sh_tokens):
    if sh_tokens[i].lex not in [
        lexer.ShellTokenType.ARG, lexer.ShellTokenType.FLAG]:
      break
    i += 1
  sh_tokens = sh_tokens[:i]

  return ParseArgs(sh_tokens)


def ParseArgs(ts):
  """Parse a list of lexer.ShellTokens as a gcloud command.

  Args:
    ts: list of lexer.ShellTokens of type ARG or FLAG.

  Returns:
    A list of ArgTokens.
  """
  if not ts:
    return []

  cur = gcloud_tree
  expected_flags = gcloud_tree['flags'].copy()
  positionals_seen = 0

  ret = []

  i = 0
  while i < len(ts):
    value = ts[i].UnquotedValue()
    if ts[i].lex == lexer.ShellTokenType.ARG:
      if value in cur['commands']:
        cur = cur['commands'][value]
        expected_flags.update(cur['flags'])

        if cur['commands']:
          token_type = ArgTokenType.GROUP
        else:
          token_type = ArgTokenType.COMMAND

        ret.append(ArgToken(value, token_type, cur, ts[i].start, ts[i].end))

      elif len(cur['positionals']) > positionals_seen:
        tree = cur['positionals'][positionals_seen]
        ret.append(ArgToken(
            value, ArgTokenType.POSITIONAL, tree, ts[i].start, ts[i].end))
        positionals_seen += 1

      else:
        ret.append(ArgToken(
            value, ArgTokenType.UNKNOWN, cur, ts[i].start, ts[i].end))

    elif ts[i].lex == lexer.ShellTokenType.FLAG:
      used, tokens = ParseFlag(cur, expected_flags, ts[i:])
      ret.extend(tokens)
      i += used
      continue

    i += 1

  return ret


def ParseFlag(cur, expected_flags, ts):
  """Parse a list of lexer.ShellTokens as a gcloud command.

  Args:
    cur: the current location in the gcloud_tree
    expected_flags: a dict containing flags from the gcloud_tree
    ts: list of lexer.ShellTokens of type ARG or FLAG where the first is FLAG.

  Returns:
    A tuple containing the number of ShellTokens used and a list of ArgTokens.
  """

  tok_str = ts[0].UnquotedValue()
  tokens_used = 1
  flag = tok_str
  value = None

  if '=' in flag:
    flag, value = tok_str.split('=', 1)

  if flag not in expected_flags:
    return 1, [ArgToken(
        tok_str, ArgTokenType.UNKNOWN, cur, ts[0].start, ts[0].end)]

  flag_def = expected_flags[flag]

  start = ts[0].start
  end = ts[0].end
  if flag_def['type'] != 'bool' and value is None and len(ts) >= 2:
    # next arg is the flag value
    end = ts[1].end
    tokens_used = 2

  return tokens_used, [
      ArgToken(tok_str, ArgTokenType.FLAG, flag_def, start, end)]
