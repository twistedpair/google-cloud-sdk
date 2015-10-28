# Copyright 2015 Google Inc. All Rights Reserved.
"""gcloud datastore emulator start command."""

from googlecloudsdk.api_lib.emulators import util
from googlecloudsdk.calliope import base


class EnvInit(base.Command):
  """Print the commands required to export a datastore emulators env variables.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To print the env variables exports for a datastore emulator, run:

            $ {command} DATA-DIR
          """,
  }

  def Run(self, args):
    return util.ReadEnvYaml(args.data_dir)

  def Display(self, args, result):
    util.PrintEnvExport(result)
