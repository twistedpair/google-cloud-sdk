# Copyright 2016 Google Inc. All Rights Reserved.
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

"""Methods for looking up completions from the static CLI tree."""

import os
import shlex

from googlecloudsdk.calliope import cli_tree


LINE_ENV_VAR = 'COMP_LINE'
POINT_ENV_VAR = 'COMP_POINT'
IFS_ENV_VAR = '_ARGCOMPLETE_IFS'
IFS_ENV_DEFAULT = '\013'
COMPLETIONS_OUTPUT_FD = 8

FLAG_BOOLEAN, FLAG_CANNOT_BE_COMPLETED, FLAG_DYNAMIC = range(3)

LOOKUP_CHOICES = 'choices'
LOOKUP_COMMANDS = 'commands'
LOOKUP_COMPLETER = 'completer'
LOOKUP_FLAGS = 'flags'
LOOKUP_IS_HIDDEN = 'hidden'
LOOKUP_NARGS = 'nargs'
LOOKUP_POSITIONALS = 'positionals'
LOOKUP_TYPE = 'type'

FLAG_PREFIX = '--'

_EMPTY_STRING = ''
_VALUE_SEP = '='
_SPACE = ' '


class CannotHandleCompletionError(Exception):
  """Error for when completions cannot be handled."""
  pass


def _GetCmdLineFromEnv():
  """Gets the command line from the environment.

  Returns:
    str, Command line.
  """
  cmd_line = os.environ.get(LINE_ENV_VAR)
  completion_point = int(os.environ.get(POINT_ENV_VAR))
  cmd_line = cmd_line[:completion_point]
  return cmd_line


def _GetCmdWordQueue(cmd_line):
  """Converts the given cmd_line to a queue of command line words.

  Args:
    cmd_line: str, full command line before parsing.

  Returns:
    [str], Queue of command line words.
  """
  cmd_words = shlex.split(cmd_line)[1:]  # First word should always be 'gcloud'

  # We need to know if last word was empty. Shlex removes trailing whitespaces.
  if cmd_line[-1] == _SPACE:
    cmd_words.append(_EMPTY_STRING)

  # Reverse so we can use as a queue
  cmd_words.reverse()
  return cmd_words


def _GetFlagMode(flag):
  """Returns the FLAG_* mode or choices list for flag."""
  choices = flag.get(LOOKUP_CHOICES, None)
  if choices:
    return choices
  if flag.get(LOOKUP_COMPLETER, None):
    return FLAG_DYNAMIC
  if flag.get(LOOKUP_TYPE, None) == 'bool':
    return FLAG_BOOLEAN
  return FLAG_CANNOT_BE_COMPLETED


def _FindCompletions(root, cmd_line):
  """Try to perform a completion based on the static CLI tree.

  Args:
    root: The root of the tree that will be traversed to find completions.
    cmd_line: [str], original command line.

  Raises:
    CannotHandleCompletionError: If FindCompletions cannot handle completion.

  Returns:
    []: No completions.
    [completions]: List, all possible sorted completions.
  """
  words = _GetCmdWordQueue(cmd_line)
  node = root

  global_flags = node[LOOKUP_FLAGS]

  completions = []
  flag_mode = FLAG_BOOLEAN
  while words:
    if node.get(LOOKUP_IS_HIDDEN, False):
      return []
    word = words.pop()

    if word.startswith(FLAG_PREFIX):
      is_flag_word = True
      child_nodes = node.get(LOOKUP_FLAGS, {})
      child_nodes.update(global_flags)
      # Add the value part back to the queue if it exists
      if _VALUE_SEP in word:
        word, flag_value = word.split(_VALUE_SEP, 1)
        words.append(flag_value)
    else:
      child_nodes = node.get(LOOKUP_COMMANDS, {})
      is_flag_word = False

    # Consume word
    if words:
      if word in child_nodes:
        if is_flag_word:
          flag = child_nodes[word]
          flag_mode = _GetFlagMode(flag)
        else:
          flag_mode = FLAG_BOOLEAN
          node = child_nodes[word]  # Progress to next command node
      elif flag_mode:
        flag_mode = FLAG_BOOLEAN
        continue  # Just consume if we are expecting a flag value
      else:
        return []  # Non-existing command/flag, so nothing to do

    # Complete word
    else:
      if flag_mode == FLAG_DYNAMIC:
        raise CannotHandleCompletionError(
            'Dynamic completions are not handled by this module')
      elif flag_mode == FLAG_CANNOT_BE_COMPLETED:
        return []  # Cannot complete, so nothing to do
      elif flag_mode:  # Must be list of choices
        for value in flag_mode:
          if value.startswith(word):
            completions.append(value)
      elif not child_nodes and node.get(LOOKUP_POSITIONALS, None):
        raise CannotHandleCompletionError(
            'Positional completions are not handled by this module')
      else:  # Command/flag completion
        for child, value in child_nodes.iteritems():
          if not child.startswith(word):
            continue
          if value.get(LOOKUP_IS_HIDDEN, False):
            continue
          if is_flag_word and _GetFlagMode(value) != FLAG_BOOLEAN:
            child += _VALUE_SEP
          completions.append(child)
  return sorted(completions)


def _OpenCompletionsOutputStream():
  """Returns the completions output stream."""
  return os.fdopen(COMPLETIONS_OUTPUT_FD, 'wb')


def Complete():
  """Attempts completions and writes them to the completion stream."""
  root = cli_tree.Load()
  cmd_line = _GetCmdLineFromEnv()

  completions = _FindCompletions(root, cmd_line)
  if completions:
    # The bash/zsh completion scripts set IFS_ENV_VAR to one character.
    ifs = os.environ.get(IFS_ENV_VAR, IFS_ENV_DEFAULT)
    # Write completions to stream
    try:
      f = _OpenCompletionsOutputStream()
      f.write(ifs.join(completions))
    finally:
      f.close()
