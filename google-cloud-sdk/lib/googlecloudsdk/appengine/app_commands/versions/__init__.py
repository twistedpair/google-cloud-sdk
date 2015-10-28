# Copyright 2015 Google Inc. All Rights Reserved.

"""The gcloud app versions group."""
from googlecloudsdk.calliope import base


@base.Hidden
class Versions(base.Group):
  """View and manage your App Engine versions.

  This set of commands can be used to view and manage your existing App Engine
  versions. To create new deployments, use `{parent_command} deploy`.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To list your deployed versions, run:

            $ {command} list
      """,
  }
