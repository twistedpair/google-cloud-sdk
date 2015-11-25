# Copyright 2013 Google Inc. All Rights Reserved.

"""A command that prints out information about your gcloud environment."""

from googlecloudsdk.api_lib.sdktool import info_holder
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core.util import platforms


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
    holder = info_holder.InfoHolder()
    python_version = platforms.PythonVersion()
    if not python_version.IsSupported():
      log.warn(('Only Python version {0} is supported for the Cloud SDK. Many '
                'commands will work with a previous version, but not all.'
               ).format(python_version.MinSupportedVersionString()))
    return holder

  def Display(self, args, info):
    log.Print(info)

    if args.show_log and info.logs.last_log:
      log.Print('\nContents of log file: [{0}]\n'
                '==========================================================\n'
                '{1}\n\n'
                .format(info.logs.last_log, info.logs.LastLogContents()))

