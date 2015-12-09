# Copyright 2015 Google Inc. All Rights Reserved.

"""The 'gcloud test android locales' command group."""

from googlecloudsdk.calliope import base


class Locales(base.Group):
  """Explore Android locales available for testing."""

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To list all available Android locales which can be used for testing
          international applications, run:

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
