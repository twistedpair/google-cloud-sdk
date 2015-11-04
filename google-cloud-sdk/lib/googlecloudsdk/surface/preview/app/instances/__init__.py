# Copyright 2015 Google Inc. All Rights Reserved.

"""The gcloud app instances group."""
from googlecloudsdk.calliope import base


@base.Hidden
class Instances(base.Group):
  """View and manage your App Engine instances.

  This set of commands can be used to view and manage your existing App Engine
  instances.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To list your App Engine instances, run:

            $ {command} list
      """,
  }
