# Copyright 2014 Google Inc. All Rights Reserved.

"""Cloud Resource Group resources sub-group."""

from googlecloudsdk.calliope import base


class Changes(base.Group):
  """Manage Resources in Cloud Resource Views."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument(
        '--resourceview', required=True, help='Resource view name.')
