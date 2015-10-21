# Copyright 2015 Google Inc. All Rights Reserved.

"""A command that lists the gcloud group and command tree with details."""

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import walker_util
from googlecloudsdk.core import resource_printer


class ListGCloud(base.Command):
  """List the gcloud CLI command tree with flag, positional and help details."""

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--hidden',
        action='store_true',
        default=None,
        help=('Include hidden commands and groups.'))
    parser.add_argument(
        'restrict',
        metavar='COMMAND/GROUP',
        nargs='*',
        default=None,
        help='Restrict the tree to the specified command groups.')

  def Run(self, args):
    return walker_util.GCloudTreeGenerator(self.cli).Walk(args.hidden,
                                                          args.restrict)

  def Display(self, unused_args, result):
    resource_printer.Print(result, 'json')
