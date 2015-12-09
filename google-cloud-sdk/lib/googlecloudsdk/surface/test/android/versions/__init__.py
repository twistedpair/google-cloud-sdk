# Copyright 2015 Google Inc. All Rights Reserved.

"""The 'gcloud test android versions' command group."""

from googlecloudsdk.calliope import base


class Versions(base.Group):
  """Explore Android versions available for testing."""

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To list information about all versions of the Android OS available
          for running tests, including details such as OS code name and
          release date, run:

            $ {command} list
          """,
  }

  @staticmethod
  def Args(parser):
    """Method called by Calliope to register flags common to this sub-group.

    Args:
      parser: An argparse parser used to add arguments that immediately follow
          this group in the CLI. Positional arguments are allowed.
    """
