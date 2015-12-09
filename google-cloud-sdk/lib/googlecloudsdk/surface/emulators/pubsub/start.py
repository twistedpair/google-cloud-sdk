# Copyright 2015 Google Inc. All Rights Reserved.
"""gcloud pubsub emulator start command."""

from googlecloudsdk.api_lib.emulators import pubsub_util
from googlecloudsdk.api_lib.emulators import util
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base


class Start(base.Command):
  """Start a local pubsub emulator.

  This command starts a local pubsub emulator.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To start a local pubsub emulator, run:

            $ {command} --data-dir DATA-DIR
          """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--host-port',
        required=False,
        type=arg_parsers.HostPort.Parse,
        help='The host:port to which the emulator should be bound.')

  # Override
  def Run(self, args):
    if not args.host_port:
      args.host_port = arg_parsers.HostPort.Parse(util.GetHostPort(
          pubsub_util.PUBSUB))

    pubsub_util.Start(args)
