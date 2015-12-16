# Copyright 2015 Google Inc. All Rights Reserved.

"""Deletes captures in a project repository.
"""

from googlecloudsdk.api_lib.source import capture
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log


class Delete(base.Command):
  """Delete source captures."""

  detailed_help = {
      'DESCRIPTION': """\
          This command deletes one or more source captures for a project.
      """
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'capture_id', metavar='ID', nargs='+',
        completion_resource='source.captures',
        help="""\
            The ID of an existing capture to delete.
        """)

  def Run(self, args):
    """Run the delete command."""
    manager = capture.CaptureManager()
    deleted_list = []
    for name in args.capture_id:
      d = manager.DeleteCapture(name)
      log.DeletedResource(d)
      deleted_list.append(d)
    return deleted_list

  def Display(self, args, deleted_list):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      deleted_list: The captures deleted by the Run() method.
    """
    log.Print('Deleted {0} captures.'.format(len(deleted_list)))
