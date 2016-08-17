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

"""Methods for looking up completions from the static completion table."""

import imp
import os
import shlex

LINE = 'COMP_LINE'
POINT = 'COMP_POINT'
IFS = '_ARGCOMPLETE_IFS'
IFS_DEFAULT = '\013'

DYNAMIC = 'DYNAMIC'
CANNOT_BE_COMPLETED = 'CANNOT_BE_COMPLETED'

COMMANDS_KEY = 'commands'
FLAGS_KEY = 'flags'
POSITIONALS_KEY = 'positionals'
FLAG_PREFIX = '--'

_EMPTY_STRING = ''
_VALUE_SEP = '='
_SPACE = ' '


class CannotHandleCompletionError(Exception):
  """Error for when completions cannot be handled."""
  pass


def LoadTable(gcloud_py_dir):
  """Returns table to be used for finding completions.

  Args:
    gcloud_py_dir: str, Directory path of currently executing gcloud.py.

  Returns:
    table: tree.
  """
  # installation root path
  table_py_path = os.path.dirname(gcloud_py_dir)
  # .install/static_completion/table.pyc
  table_py_path = os.path.join(table_py_path, '.install', 'static_completion',
                               'table.py')

  # Load table using relative path and return
  return imp.load_source('static_completion_table', table_py_path).table


def _GetCmdLineFromEnv():
  """Gets the command line from the environment.

  Returns:
    str, Command line.
  """
  cmd_line = os.environ.get(LINE)
  completion_point = int(os.environ.get(POINT))
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


def _OpenCompletionsStream():
  return os.fdopen(8, 'wb')


def _CloseCompletionsStream(file_object):
  file_object.close()


def Complete(gcloud_py_dir):
  """Attemps to do completions and successful completions are written to stream.

  Args:
    gcloud_py_dir: str, Directory path of currently executing gcloud.py.
  """
  node = LoadTable(gcloud_py_dir)
  cmd_line = _GetCmdLineFromEnv()

  completions = FindCompletions(node, cmd_line)
  if completions:
    # The bash/zsh completion scripts set IFS to one character.
    ifs = os.environ.get(IFS, IFS_DEFAULT)
    # Write completions to stream
    out_stream = _OpenCompletionsStream()
    out_stream.write(ifs.join(completions))
    out_stream.flush()
    _CloseCompletionsStream(out_stream)


def FindCompletions(table, cmd_line):
  """Try to perform a completion based on the static completion table.

  Args:
    table: Tree that will be traversed to find completions.
    cmd_line: [str], original command line.

  Returns:
    []: No completions.
    [completions]: List, all possible sorted completions.

  Raises:
    CannotHandleCompletionError: If FindCompletions cannot handle completion.
  """
  words = _GetCmdWordQueue(cmd_line)
  node = table

  global_flags = node[FLAGS_KEY]

  completions = []
  flag_value_mode = None
  while words:
    word = words.pop()

    if word.startswith(FLAG_PREFIX):
      is_flag_word = True
      child_nodes = node.get(FLAGS_KEY, {})
      child_nodes.update(global_flags)
      # Add the value part back to the queue if it exists
      if _VALUE_SEP in word:
        word, flag_value = word.split(_VALUE_SEP, 1)
        words.append(flag_value)
    else:
      child_nodes = node.get(COMMANDS_KEY, {})
      is_flag_word = False

    # Consume word
    if words:
      if word in child_nodes:
        if is_flag_word:
          flag_value_mode = child_nodes[word]
        else:
          flag_value_mode = None
          node = child_nodes[word]  # Progress to next command node
      elif flag_value_mode:
        flag_value_mode = None
        continue  # Just consume if we are expecting a flag value
      else:
        return []  # Non-existing command/flag, so nothing to do

    # Complete word
    else:
      if flag_value_mode == DYNAMIC:
        raise CannotHandleCompletionError(
            'Dynamic completions are not handled by this module')
      elif flag_value_mode == CANNOT_BE_COMPLETED:
        return []  # Cannot complete, so nothing to do
      elif flag_value_mode:  # Must be list of choices
        for value in flag_value_mode:
          if value.startswith(word):
            completions.append(value)
      elif not child_nodes and node.get(POSITIONALS_KEY, None):
        raise CannotHandleCompletionError(
            'Completion of positionals is not handled by this module')
      else:  # Command/flag completion
        for child, value in child_nodes.iteritems():
          if not child.startswith(word):
            continue
          if is_flag_word and value:
            child += _VALUE_SEP
          completions.append(child)
  completions.sort()
  return completions
