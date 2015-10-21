# Copyright 2013 Google Inc. All Rights Reserved.

"""A command that prints out information about your gcloud environment."""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.shared.sdktool import info_holder


@base.ReleaseTracks(base.ReleaseTrack.GA)
class Info(base.Command):
  """Display information about the current gcloud environment.

     This command displays information about the current gcloud environment.
  """

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--show-log',
        action='store_true',
        help='Print the contents of the last log file.')

  def Run(self, args):
    return info_holder.InfoHolder()

  def Display(self, args, info):
    log.Print(info)

    if args.show_log and info.logs.last_log:
      log.Print('\nContents of log file: [{0}]\n'
                '==========================================================\n'
                '{1}\n\n'
                .format(info.logs.last_log, info.logs.LastLogContents()))

