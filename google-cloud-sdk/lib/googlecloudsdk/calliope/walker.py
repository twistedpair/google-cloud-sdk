# Copyright 2015 Google Inc. All Rights Reserved.

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
      restrict: Restricts the walk to the top level command/group names in this
        list. For example, restrict=['compute'] will list 'gcloud' and the
        'gcloud compute *' commands/groups.

    Returns:
      The return value of the top level Visit() call.
    """
    def _Include(command, restrict):
      """Determines if command should be included in the walk.

      Args:
        command: CommandCommon command node.
        restrict: Restricts the walk to the top level subcommand/subgroup names
          in this list.

      Returns:
        True if command should be included in the walk.
      """
      if not hidden and command.IsHidden():
        return False
      if restrict and command.name not in restrict:
        return False
      return True

    def _Walk(node, parent, restrict=None):
      """Walk() helper that calls self.Visit() on each node in the CLI tree.

      Args:
        node: CommandCommon tree node.
        parent: The parent Visit() return value, None at the top level.
        restrict: Restricts the walk to the top level subcommand/subgroup names
          in this list.

      Returns:
        The return value of the outer Visit() call.
      """
      parent = self.Visit(node, parent, is_group=True)
      if node.commands:
        for _, command in sorted(node.commands.iteritems()):
          if _Include(command, restrict):
            self.Visit(command, parent, is_group=False)
      if node.groups:
        for _, command in sorted(node.groups.iteritems()):
          if _Include(command, restrict):
            _Walk(command, parent)
      return parent

    root = self._cli._TopElement()  # pylint: disable=protected-access
    root.LoadAllSubElements(recursive=True)
    parent = _Walk(root, self.Init(), restrict=restrict)
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
