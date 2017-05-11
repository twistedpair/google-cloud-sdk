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
    self.flag_groups = {}
    self.positionals = []

    for token in tokens:
      if token.token_type == ArgTokenType.COMMAND:
        self.command = token
      elif token.token_type == ArgTokenType.GROUP:
        self.groups.append(token)
      elif token.token_type == ArgTokenType.FLAG:
        self.flags.append(token)
        flag_group = token.tree.get('group', None)
        if flag_group:
          flag_group_properties = self.GetPossibleFlagGroups().get(flag_group)
          if flag_group_properties:
            self.flag_groups[flag_group] = flag_group_properties
      elif token.token_type == ArgTokenType.POSITIONAL:
        self.positionals.append(token)

  def GetCommandOrGroup(self):
    """Get the command or last group."""
    if self.command:
      return self.command

    if self.groups:
      return self.groups[-1]

    return None

  def GetPossibleFlags(self):
    """Get all the flags for the groups and command of this invocation."""
    flags = {}
    for group in self.groups:
      flags.update(group.tree.get('flags', {}))

    if self.command:
      flags.update(self.command.tree.get('flags', {}))

    return flags

  def GetPossibleFlagGroups(self):
    flag_groups = {}
    for group in self.groups:
      flag_groups.update(group.tree.get('groups', {}))
    if self.command:
      flag_groups.update(self.command.tree.get('groups', {}))
    return flag_groups

  def GetPossibleCommandGroups(self):
    """Get all the possible commands for the current group."""
    if (not self.tokens) or (self.tokens[-1].token_type != ArgTokenType.GROUP):
      return []
    group = self.tokens[-1]
    return group.tree.get('commands', {}).keys()


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


def TokenIsArgument(token):
  """Checks whether a given token is an argument.

  Args:
    token: a lexer.ShellToken

  Returns:
    True if the token is of type lexer.ShellTokenType.ARG, False otherwise.
  """
  return token.lex == lexer.ShellTokenType.ARG


def TokenIsFlag(token):
  """Checks whether a given token is a flag.

  Args:
    token: a lexer.ShellToken

  Returns:
    True if the token is a flag, False otherwise.
  """
  return TokenIsArgument(token) and token.value.startswith('-')


def TokenIsTerminator(token):
  """Checks whether a given token is a terminator.

  Args:
    token: a lexer.ShellToken

  Returns:
    True if the token is of type lexer.ShellTokenType.TERMINATOR, False
    otherwise.
  """
  return token.lex == lexer.ShellTokenType.TERMINATOR


def ParseLine(line):
  """Parse a gcloud command line.

  Args:
    line: a string containing one or more gcloud invocations

  Returns:
    A list of GcloudInvocations, one for each command in the line (delimited by
    terminators).
  """
  sh_tokens = lexer.GetShellTokens(line)
  if not sh_tokens:
    return []

  parsed_line = []
  current_invocation = []

  # Separate parsed line into invocations based on terminators
  while sh_tokens:
    current_token = sh_tokens.pop(0)
    if TokenIsArgument(current_token):
      current_invocation.append(current_token)
    elif TokenIsTerminator(current_token):
      parsed_line.append(GcloudInvocation(ParseArgs(current_invocation)))
      current_invocation = []
    else:
      # Ignore the rest of the current invocation if the token is not of type
      # ShellTokenType.ARG (that is, if it's of type IO, REDIRECTION, FILE or
      # TRAILING_BACKSLASH)
      while sh_tokens:
        if TokenIsTerminator(sh_tokens.pop(0)):
          break
  # Add the last current_invocation
  parsed_line.append(GcloudInvocation(ParseArgs(current_invocation)))
  return parsed_line


def ParseArgs(ts):
  """Parse a list of lexer.ShellTokens as a gcloud command.

  Args:
    ts: list of lexer.ShellTokens of type ARG.

  Returns:
    A list of ArgTokens.

  Raises:
    ValueError: if not all lexer.ShellTokens in ts are of type ARG.
  """
  if not ts:
    return []

  cur = gcloud_tree
  expected_flags = gcloud_tree['flags'].copy()
  positionals_seen = 0

  ret = []

  i = 0
  while i < len(ts):
    current_token = ts[i]
    if not TokenIsArgument(current_token):
      raise ValueError(
          ('Lexer tokens passed to this function should only be of type ARG: '
           '{}').format(current_token))

    if TokenIsFlag(current_token):
      used, tokens = ParseFlag(cur, expected_flags, ts[i:])
      ret.extend(tokens)
      i += used
      continue
    else:
      value = current_token.UnquotedValue()
      if value in cur['commands']:
        cur = cur['commands'][value]
        expected_flags.update(cur['flags'])

        if cur.get('commands'):
          token_type = ArgTokenType.GROUP
        else:
          token_type = ArgTokenType.COMMAND

        ret.append(ArgToken(value, token_type, cur, current_token.start,
                            current_token.end))

      elif len(cur['positionals']) > positionals_seen:
        tree = cur['positionals'][positionals_seen]
        ret.append(ArgToken(
            value, ArgTokenType.POSITIONAL, tree, current_token.start,
            current_token.end))
        positionals_seen += 1
      else:
        ret.append(ArgToken(
            value, ArgTokenType.UNKNOWN, cur, current_token.start,
            current_token.end))
    i += 1

  return ret


def ParseFlag(cur, expected_flags, ts):
  """Parse a gcloud flag.

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

  name_start = ts[0].start
  name_end = ts[0].end
  value_start = None
  value_end = None

  if '=' in flag:
    flag, value = tok_str.split('=', 1)
    name_end = name_start + len(flag)
    value_start = name_end + 1
    value_end = value_start + len(value)

  if flag not in expected_flags:
    return 1, [ArgToken(
        tok_str, ArgTokenType.UNKNOWN, cur, ts[0].start, ts[0].end)]

  flag_def = expected_flags[flag]
  token_list = [
      ArgToken(flag, ArgTokenType.FLAG, flag_def, name_start, name_end)]

  if flag_def['type'] != 'bool':
    if value is None and len(ts) >= 2:
      # next arg is the flag value
      tokens_used = 2
      value = ts[1].UnquotedValue()
      value_start = ts[1].start
      value_end = ts[1].end

  if value is not None:
    token_list.append(ArgToken(
        value, ArgTokenType.FLAG_ARG, flag_def, value_start, value_end))

  return tokens_used, token_list
