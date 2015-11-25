# Copyright 2013 Google Inc. All Rights Reserved.

"""The command to remove gcloud components."""

import argparse

from googlecloudsdk.calliope import base


class Remove(base.Command):
  """Remove one or more installed components.

  Uninstall all listed components, as well as all components that directly or
  indirectly depend on them.
  """

  detailed_help = {
      'DESCRIPTION': """\
          Uninstall all listed components, as well as all components that
          directly or indirectly depend on them.

          The command lists all components it is about to remove, and asks for
          confirmation before proceeding.
      """,
      'EXAMPLES': """\
          To remove ``COMPONENT-1'', ``COMPONENT-2'', and all components that
          directly or indirectly depend on ``COMPONENT-1'' or ``COMPONENT-2'',
          type the following:

            $ {command} COMPONENT-1 COMPONENT-2
      """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'component_ids',
        metavar='COMPONENT-ID',
        nargs='+',
        help='The IDs of the components to be removed.')
    parser.add_argument(
        '--allow-no-backup',
        required=False,
        action='store_true',
        help=argparse.SUPPRESS)

  def Run(self, args):
    """Runs the list command."""
    self.group.update_manager.Remove(
        args.component_ids, allow_no_backup=args.allow_no_backup)
