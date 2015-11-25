# Copyright 2013 Google Inc. All Rights Reserved.

"""The Run command."""

import argparse

from googlecloudsdk.calliope import base
from googlecloudsdk.core import log


class Run(base.Command):
  """(REMOVED) Run one or more modules in the local development server.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          This command is deprecated. Please use the dev_appserver.py script
          instead.
          """,
  }

  @staticmethod
  def Args(parser):
    # REMAINDER means this will match for any set of arguments. We don't want
    # to error on bad flags, we want to print the general error message no
    # matter what.
    parser.add_argument('unused', nargs=argparse.REMAINDER)

  def Run(self, args):
    log.error('Please use the bundled dev_appserver.py script instead.')
