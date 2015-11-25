# Copyright 2015 Google Inc. All Rights Reserved.
"""`gcloud app services list` command."""

from googlecloudsdk.api_lib.app import appengine_client
from googlecloudsdk.calliope import base


class List(base.Command):
  """List your existing services.

  This command lists all services that are currently deployed to the App Engine
  server.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To list all services in the current project, run:

            $ {command}

          """,
  }

  @staticmethod
  def Collection(unused_args):
    return 'app.services'

  def Run(self, args):
    return appengine_client.AppengineClient().ListServices()
