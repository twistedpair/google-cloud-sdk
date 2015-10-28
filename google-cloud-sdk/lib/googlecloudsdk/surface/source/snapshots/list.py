# Copyright 2015 Google Inc. All Rights Reserved.

"""List snapshots in a project repository.
"""

from googlecloudsdk.api_lib.source import snapshot
from googlecloudsdk.calliope import base
from googlecloudsdk.core import list_printer


class List(base.Command):
  """List source snapshots."""

  detailed_help = {
      'DESCRIPTION': """\
          This command displays a list of the source snapshots for a project.
          Source snapshots enable cloud diagnostics tools such as the Cloud
          Debugger to work with a copy of the source code corresponding to a
          deployed binary.
      """
  }

  def Run(self, args):
    """Run the snapshot command."""
    mgr = snapshot.SnapshotManager()
    return mgr.ListSnapshots()

  def Display(self, args, snapshots):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      snapshots: The value returned from the Run() method.
    """
    list_printer.PrintResourceList('source.snapshots.list', snapshots)
