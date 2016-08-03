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

"""A module for walking the Cloud SDK CLI tree."""


class Walker(object):
  """Base class for walking the Cloud SDK CLI tree.

  Attributes:
    _cli: The Cloud SDK CLI object.
  """

  def __init__(self, cli):
    """Constructor.

    Args:
      cli: The Cloud SDK CLI object.
    """
    self._cli = cli

  def Walk(self, hidden=False, restrict=None):
    """Calls self.Visit() on each node in the CLI tree.

    The walk is DFS, ordered by command name for reproducability.

    Args:
      hidden: Include hidden groups and commands if True.
      restrict: Restricts the walk to the command/group dotted paths in this
        list. For example, restrict=['gcloud.alpha.test', 'gcloud.topic']
        restricts the walk to the 'gcloud topic' and 'gcloud alpha test'
        commands/groups.

    Returns:
      The return value of the top level Visit() call.
    """
    def _Include(command, traverse=False):
      """Determines if command should be included in the walk.

      Args:
        command: CommandCommon command node.
        traverse: If True then check traversal through group to subcommands.

      Returns:
        True if command should be included in the walk.
      """
      if not hidden and command.IsHidden():
        return False
      if not restrict:
        return True
      path = '.'.join(command.GetPath())
      for item in restrict:
        if path.startswith(item):
          return True
        if traverse and item.startswith(path):
          return True
      return False

    def _Walk(node, parent):
      """Walk() helper that calls self.Visit() on each node in the CLI tree.

      Args:
        node: CommandCommon tree node.
        parent: The parent Visit() return value, None at the top level.

      Returns:
        The return value of the outer Visit() call.
      """
      parent = self.Visit(node, parent, is_group=True)
      commands_and_groups = []
      if node.commands:
        for name, command in node.commands.iteritems():
          if _Include(command):
            commands_and_groups.append((name, command, False))
      if node.groups:
        for name, command in node.groups.iteritems():
          if _Include(command, traverse=True):
            commands_and_groups.append((name, command, True))
      for _, command, is_group in sorted(commands_and_groups):
        if is_group:
          _Walk(command, parent)
        else:
          self.Visit(command, parent, is_group=False)
      return parent

    root = self._cli._TopElement()  # pylint: disable=protected-access
    root.LoadAllSubElements(recursive=True)
    parent = _Walk(root, self.Init())
    self.Done()
    return parent

  def Visit(self, node, parent, is_group):
    """Visits each node in the CLI command tree.

    Called preorder by WalkCLI() using DFS.

    Args:
      node: group/command CommandCommon info.
      parent: The parent Visit() return value, None at the top level.
      is_group: True if node is a group, otherwise its is a command.

    Returns:
      A new parent value for the node subtree. This value is the parent arg
      for the Vistit() calls for the children of this node.
    """
    pass

  def Init(self):
    """Sets up before any node in the CLI tree has been visited.

    Returns:
      The initial parent value for the first Visit() call.
    """
    return None

  def Done(self):
    """Cleans up after all nodes in the CLI tree have been visited."""
    pass
