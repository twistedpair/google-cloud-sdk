# Copyright 2014 Google Inc. All Rights Reserved.

"""gcloud dns project-info command group."""

from googlecloudsdk.calliope import base


class ProjectInfo(base.Group):
  """View Cloud DNS related information for a project."""

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To display Cloud DNS related information for your project, run:

            $ {command} describe
          """,
  }
