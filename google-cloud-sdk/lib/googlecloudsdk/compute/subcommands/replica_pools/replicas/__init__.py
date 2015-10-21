# Copyright 2014 Google Inc. All Rights Reserved.

"""replica-pools replicas sub-group."""

from googlecloudsdk.calliope import base


class Replicas(base.Group):
  """Manage replicas in a replica pool."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument(
        '--pool', required=True, help='Replica pool Name')
