# Copyright 2014 Google Inc. All Rights Reserved.

"""The 'gcloud test android' sub-group."""

from googlecloudsdk.calliope import base


class Android(base.Group):
  """Command group for Android application testing."""

  detailed_help = {
      'DESCRIPTION': """\
          Explore physical and virtual Android devices and Android OS versions
          which are available as test targets. Also run tests against your
          Android app on these devices, monitor your test progress, and view
          detailed test results in the Google Developers Console.
          """,

      'EXAMPLES': """\
          To see a list of available Android devices, their form factors, and
          supported Android OS versions, run:

            $ {command} devices list

          To view details about available Android OS versions, such as their
          code names and release dates, run:

            $ {command} versions list

          To view the list of available Android locales which can be used for
          testing internationalized applications, run:

            $ {command} locales list

          To view all options available for running Android tests, run:

            $ {command} run --help
      """
  }

  @staticmethod
  def Args(parser):
    """Method called by Calliope to register flags common to this sub-group.

    Args:
      parser: An argparse parser used to add arguments that immediately follow
          this group in the CLI. Positional arguments are allowed.
    """
