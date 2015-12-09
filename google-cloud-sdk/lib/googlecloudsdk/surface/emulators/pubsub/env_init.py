# Copyright 2015 Google Inc. All Rights Reserved.
"""gcloud pubsub emulator env_init command."""

from googlecloudsdk.api_lib.emulators import util
from googlecloudsdk.calliope import base


class EnvInit(base.Command):
  """Print the commands required to export pubsub emulator's env variables."""

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To print the env variables exports for a pubsub emulator, run:

            $ {command} --data-dir DATA-DIR
          """,
  }

  def Run(self, args):
    return util.ReadEnvYaml(args.data_dir)

  def Display(self, args, result):
    util.PrintEnvExport(result)
