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

"""Methods for managing the static completion table."""

import compileall
import os
from pprint import pprint

from googlecloudsdk.calliope import walker
from googlecloudsdk.command_lib.static_completion import lookup
from googlecloudsdk.core import config
from googlecloudsdk.core.util import files


_HYPHEN = '-'
_UNDERSCORE = '_'
_COMPLETER_ATTR = 'completer'
_COMPLETION_RESOURCE_ATTR = 'completion_resource'


def _CompletionValueType(arg):
  if arg.choices:
    return sorted(arg.choices)
  elif (getattr(arg, _COMPLETER_ATTR, None) or
        getattr(arg, _COMPLETION_RESOURCE_ATTR, None)):
    return lookup.DYNAMIC
  elif arg.nargs == 0:
    return None
  else:
    return lookup.CANNOT_BE_COMPLETED


class CompletionTableGenerator(walker.Walker):
  """Generates a static completion table by walking the gcloud CLI tree."""

  def __init__(self, cli, ignore_load_errors=False):
    """Constructor.

    Args:
      cli: The Cloud SDK CLI object.
      ignore_load_errors: bool, True to ignore command load failures. This
        should only be used when it is not critical that all data is returned,
        like for optimizations like static tab completion.
    """
    super(CompletionTableGenerator, self).__init__(
        cli, ignore_load_errors=ignore_load_errors)
    self.global_flags = set()

  def _VisitFlags(self, flags, at_root):
    """Visits all the flags for a node and contructs the required dict.

    Args:
      flags: The flag args of the current command.
      at_root: bool, Whether the current command is the top level.

    Returns:
      The appropriate flags dict with required information.
    """
    flags_dict = {}
    for flag in flags:
      for flag_name in flag.option_strings:
        if not flag_name.startswith(lookup.FLAG_PREFIX):
          continue

        flag_name = flag_name.replace(_UNDERSCORE, _HYPHEN)
        if at_root:
          self.global_flags.add(flag_name)
        elif flag_name in self.global_flags:
          # Global flags are only included in the root node.
          continue

        flags_dict[flag_name] = _CompletionValueType(flag)

    return flags_dict

  def _VisitPositionals(self, positionals, at_root):
    """Visits all the positionals for a node and contructs the required dict.

    Args:
      positionals: The positional args of the current command.
      at_root: bool, Whether the current command is the top level.

    Returns:
      The appropriate positionals dict with required information.
    """
    positionals_dict = {}
    for positional in positionals:
      positional_name = positional.dest.replace(_UNDERSCORE, _HYPHEN)
      positionals_dict[positional_name] = _CompletionValueType(positional)
    return positionals_dict

  def Visit(self, node, parent, is_group):
    """Visits each node in the CLI command tree to construct the external rep.

    Args:
      node: group/command CommandCommon info.
      parent: The parent Visit() return value, None at the top level.
      is_group: True if node is a group, otherwise its is a command.

    Returns:
      The subtree parent value, used here to construct an external rep node.
    """
    command = {}

    name = node.name.replace(_UNDERSCORE, _HYPHEN)
    # Add to parent's children
    if parent:
      siblings = parent.get(lookup.COMMANDS_KEY, {})
      siblings[name] = command
      parent[lookup.COMMANDS_KEY] = siblings

    # Populate flags
    command[lookup.FLAGS_KEY] = self._VisitFlags(
        node.GetAllAvailableFlags(include_global=parent is None,
                                  include_hidden=False),
        parent is None)

    # Populate positionals
    command[lookup.POSITIONALS_KEY] = self._VisitPositionals(
        node.ai.positional_args, parent is None)

    return command


def _TableDirPath():
  paths = config.Paths()
  # Completion table will be stored at root/.install/static_completion.
  table_dir_path = os.path.join(paths.sdk_root, paths.CLOUDSDK_STATE_DIR,
                                'static_completion')
  # Ensure directory exists.
  files.MakeDir(table_dir_path)

  return table_dir_path


def _TablePath():
  return os.path.join(_TableDirPath(), 'table.py')


def Update(cli):
  """Create or overwrite static completion table.

  Args:
    cli: Calliope CLI object for generating the completion table.
  """
  # Overwrite the completion table file with updated content
  with open(_TablePath(), 'w') as table_file:
    table = CompletionTableGenerator(
        cli, ignore_load_errors=True).Walk(hidden=False)
    table_file.write('table=')
    pprint(table, table_file)
  # _TableDirPath() could contain unicode chars and py_compile chokes on unicode
  # paths. Using relative paths from _TableDirPath() works around the problem.
  table_dir_path = _TableDirPath()
  with files.ChDir(table_dir_path):
    # Pre-compile table source to enable fast loading
    compileall.compile_dir('.', quiet=True)
