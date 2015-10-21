# Copyright 2014 Google Inc. All Rights Reserved.

"""gcloud dns record-sets changes command group."""

from googlecloudsdk.calliope import base


class Changes(base.Group):
  """View details about changes to your Cloud DNS record-sets."""

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To view the details of a particular change, run:

            $ {command} describe CHANGE_ID -z MANAGED_ZONE

          To view the list of all changes, run:

            $ {command} list -z MANAGED_ZONE
          """,
  }
