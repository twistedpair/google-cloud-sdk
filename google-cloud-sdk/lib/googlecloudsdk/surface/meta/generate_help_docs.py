# Copyright 2015 Google Inc. All Rights Reserved.

"""A command that generates all DevSite and manpage documents."""

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import walker_util


class GenerateHelpDocs(base.Command):
  """Generate all DevSite and man page help docs.

  The DevSite docs are generated in the --devsite-dir directory with pathnames
  in the reference directory hierarchy. The manpage docs are generated in the
  --manpage-dir directory with pathnames in the manN/ directory hierarchy.
  """

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--hidden',
        action='store_true',
        default=None,
        help=('Include documents for hidden commands and groups.'))
    parser.add_argument(
        '--devsite-dir',
        metavar='DIRECTORY',
        help=('The directory where the generated DevSite reference document '
              'subtree will be written. If not specified then DevSite '
              'documents will not be generated.'))
    parser.add_argument(
        '--manpage-dir',
        metavar='DIRECTORY',
        help=('The directory where generated manpage document subtree will be '
              'written. If not specified then manpage documents will not be '
              'generated.'))
    parser.add_argument(
        'restrict',
        metavar='COMMAND/GROUP',
        nargs='*',
        default=None,
        help='Restrict the document generation to the specified commands '
        'and/or groups.')

  def Run(self, args):
    if args.devsite_dir:
      walker_util.DevSiteGenerator(self.cli, args.devsite_dir).Walk(
          args.hidden, args.restrict)
    if args.manpage_dir:
      walker_util.ManPageGenerator(self.cli, args.manpage_dir).Walk(
          args.hidden, args.restrict)
