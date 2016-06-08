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


def _LoadTable(gcloud_py_dir):
  # installation root path
  table_py_path = os.path.dirname(gcloud_py_dir)
  # .install/static_completion/table.pyc
  table_py_path = os.path.join(table_py_path, '.install', 'static_completion',
                               'table.py')

  # Load table using relative path and return
  return imp.load_source('static_completion_table', table_py_path).table


def _CmdWordQueue():
  """Converts the command line into a queue of words to be used for completion.

  Returns:
    [str], Queue of command line words.
  """
  cmd_line = os.environ.get(LINE)
  completion_point = int(os.environ.get(POINT))
  cmd_line = cmd_line[:completion_point]
  cmd_words = shlex.split(cmd_line)[1:]  # First word should always be 'gcloud'

  # We need to know if last word was empty. Shlex removes trailing whitespaces.
  if cmd_line[-1] == _SPACE:
    cmd_words.append(_EMPTY_STRING)

  # Reverse so we can use as a queue
  cmd_words.reverse()
  return cmd_words


def _OpenCompletionsStream():
  return os.fdopen(8, 'wb')


def Complete(gcloud_py_dir):
  """Try to perform a completion based on the static completion table.

  Args:
    gcloud_py_dir: str, Directory path of currently executing gcloud.py.

  Returns:
    bool, True if completion was performed, False otherwise.
  """
  words = _CmdWordQueue()
  node = _LoadTable(gcloud_py_dir)
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
        return True  # Non-existing command/flag, so nothing to do

    # Complete word
    else:
      if flag_value_mode == DYNAMIC:
        return False  # Fall back to dynamic completion
      elif flag_value_mode == CANNOT_BE_COMPLETED:
        return True  # Cannot complete, so nothing to do
      elif flag_value_mode:  # Must be list of choices
        for value in flag_value_mode:
          if value.startswith(word):
            completions.append(value)
      elif not child_nodes and node.get(POSITIONALS_KEY, None):
        return False  # Fall back to dynamic completion
      else:  # Command/flag completion
        for child, value in child_nodes.iteritems():
          if not child.startswith(word):
            continue
          if is_flag_word and value:
            child += _VALUE_SEP
          completions.append(child)

  # Write completions to stream
  completions.sort()
  # The bash/zsh completion scripts set IFS to one character.
  ifs = os.environ.get(IFS, IFS_DEFAULT)
  out_stream = _OpenCompletionsStream()
  out_stream.write(ifs.join(completions))
  out_stream.flush()

  return True
