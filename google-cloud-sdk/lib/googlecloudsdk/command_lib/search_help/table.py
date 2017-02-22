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

"""Library to help build the help search table."""

import json
import os

from googlecloudsdk.calliope import cli_tree
from googlecloudsdk.calliope import walker
from googlecloudsdk.core import config
from googlecloudsdk.core import log
from googlecloudsdk.core.resource import resource_projector
from googlecloudsdk.core.util import files


def _IndexDirPath():
  paths = config.Paths()
  # Table will be stored at root/.install/help_text.
  index_dir_path = os.path.join(paths.sdk_root, paths.CLOUDSDK_STATE_DIR,
                                'help_text')
  # Ensure directory exists.
  files.MakeDir(index_dir_path)

  return index_dir_path


def IndexPath():
  return os.path.join(_IndexDirPath(), 'table.json')


def Update(cli):
  """Create or overwrite help search table.

  Args:
    cli: Calliope CLI object for generating the help search table.
  """
  help_text = HelpIndexGenerator(cli).Walk(hidden=False)
  def SerializeCommand(command):
    return resource_projector.Compile().Evaluate(command)

  help_text = SerializeCommand(help_text)

  # Overwrite the help search table file with updated content
  table_path = IndexPath()
  with open(table_path, 'w') as index_file:
    json.dump(
        help_text, index_file, sort_keys=True, indent=2, separators=(',', ':'))
    index_file.write('\n')
  log.warn('updated help index at {0}'.format(table_path))


class HelpIndexGenerator(walker.Walker):
  """Constructs a CLI command help index.

  This class generates a cli_tree.Command representation of each node in the
  cli, with hidden flags removed. The Walk method calls Visit on each node
  in the CLI (depth first).

  Attributes:
    _cli: The Cloud SDK CLI object
  """

  def __init__(self, cli):
    """Constructor.

    Args:
      cli: The Cloud SDK CLI object.
    """
    super(HelpIndexGenerator, self).__init__(cli)

  def Visit(self, node, parent, is_group):
    """Implements the Visit method in calliope.walker.Walker.

    Visits each node in the CLI command tree and constructs a cli_tree.Command
    representation of it, minus any hidden flags.

    Args:
      node: calliope.base._Common group/command CommandCommon info.
      parent: The parent Visit() return value, None at the top level.
      is_group: True if node is a group, otherwise it is a command.

    Returns:
      The command path list.
    """
    command = cli_tree.Command(node, parent, include_hidden_flags=False)
    return command
