# Copyright 2015 Google Inc. All Rights Reserved.
"""The gcloud datastore emulator group."""

from googlecloudsdk.calliope import base
from googlecloudsdk.shared.emulators import datastore_util


class Datastore(base.Group):
  """Manage your local datastore emulator.

  This set of commands allows you to start and use a local datastore emulator.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To start a local datastore emulator, run:

            $ {command} start
          """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--data-dir',
        required=False,
        help='The directory to be used to store/retrieve data/config for an'
        ' emulator run.')

  def Filter(self, context, args):
    datastore_util.CheckIfJava7IsInstalled()
    datastore_util.EnsureGCDComponentIsInstalled()

    if not args.data_dir:
      args.data_dir = datastore_util.GetDataDir()
