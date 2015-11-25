# Copyright 2015 Google Inc. All Rights Reserved.

"""The gcloud app services group."""
from googlecloudsdk.calliope import base


@base.Hidden
class Services(base.Group):
  """View and manage your App Engine services.

  This set of commands can be used to view and manage your existing App Engine
  services. To create new deployments, use `{parent_command} deploy`.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To list your deployed services, run:

            $ {command} list
      """,
  }
