# Copyright 2015 Google Inc. All Rights Reserved.

"""Deletes snapshots in a project repository.
"""

from googlecloudsdk.api_lib.source import snapshot
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log


class Delete(base.Command):
  """Delete source snapshots."""

  detailed_help = {
      'DESCRIPTION': """\
          This command deletes one or more source snapshots for a project.
      """
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'snapshot_id', metavar='ID', nargs='+',
        completion_resource='source.snapshots',
        help="""\
            The ID of an existing snapshot to delete.
        """)

  def Run(self, args):
    """Run the delete command."""
    manager = snapshot.SnapshotManager()
    deleted_list = []
    for name in args.snapshot_id:
      d = manager.DeleteSnapshot(name)
      log.DeletedResource(d)
      deleted_list.append(d)
    return deleted_list

  def Display(self, args, deleted_list):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      deleted_list: The snapshots deleted by the Run() method.
    """
    log.Print('Deleted {0} snapshots.'.format(len(deleted_list)))
