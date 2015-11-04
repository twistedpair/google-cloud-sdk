# Copyright 2013 Google Inc. All Rights Reserved.

"""The gcloud app modules group."""
from googlecloudsdk.calliope import base


class Modules(base.Group):
  """View and manage your App Engine modules.

  This set of commands can be used to view and manage your existing App Engine
  modules.  To create new deployments of modules, use {parent_command} deploy.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To list your deployed modules, run:

            $ {command} list
      """,
  }
