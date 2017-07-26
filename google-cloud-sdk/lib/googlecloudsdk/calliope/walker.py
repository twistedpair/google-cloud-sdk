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

from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.console import progress_tracker


class Walker(object):
  """Base class for walking the Cloud SDK CLI tree.

  Attributes:
    _root: The root element of the CLI tree.
    _num_nodes: The total number of nodes in the tree.
    _num_visited: The count of visited nodes so far.
    _progress_callback: The progress bar function to call to update progress.
  """

  def __init__(self, cli, progress_callback=None, ignore_load_errors=False):
    """Constructor.

    Args:
      cli: The Cloud SDK CLI object.
      progress_callback: f(float), The function to call to update the progress
        bar or None for no progress bar.
      ignore_load_errors: bool, True to ignore command load failures. This
        should only be used when it is not critical that all data is returned,
        like for optimizations like static tab completion.
    """
    self._root = cli._TopElement()  # pylint: disable=protected-access
    if progress_callback:
      with progress_tracker.ProgressTracker('Loading CLI Tree'):
        self._num_nodes = 1.0 + self._root.LoadAllSubElements(
            recursive=True, ignore_load_errors=ignore_load_errors)
    else:
      self._num_nodes = 1.0 + self._root.LoadAllSubElements(
          recursive=True, ignore_load_errors=ignore_load_errors)
    self._num_visited = 0
    self._progress_callback = (progress_callback or
                               console_io.ProgressBar.DEFAULT_CALLBACK)

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
      parent = self._Visit(node, parent, is_group=True)
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
          self._Visit(command, parent, is_group=False)
      return parent

    self._num_visited = 0
    parent = _Walk(self._root, self.Init())
    self.Done()
    return parent

  def _Visit(self, node, parent, is_group):
    self._num_visited += 1
    self._progress_callback(self._num_visited/self._num_nodes)
    return self.Visit(node, parent, is_group)

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
