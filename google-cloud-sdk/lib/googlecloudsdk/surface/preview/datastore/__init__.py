# Copyright 2013 Google Inc. All Rights Reserved.

"""The gcloud datastore group."""
from googlecloudsdk.calliope import base


@base.Beta
class Datastore(base.Group):
  """Manage your Cloud Datastore.

  This set of commands allows you to create and delete datastore indexes.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To create new indexes from a file, run:

            $ {command} create-indexes index.yaml

          To clean up unused indexes from a file, run:

            $ {command} cleanup-indexes index.yaml
          """,
  }
