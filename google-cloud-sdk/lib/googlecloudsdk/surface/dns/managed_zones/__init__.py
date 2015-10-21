# Copyright 2014 Google Inc. All Rights Reserved.

"""gcloud dns managed-zones command group."""

from googlecloudsdk.calliope import base


class ManagedZones(base.Group):
  """Manage your Cloud DNS managed-zones."""

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To create a managed-zone, run:

            $ {command} create my_zone --description="My Zone" --dns-name="my.zone.com."

          To delete a managed-zone, run:

            $ {command} delete my_zone

          To view the details of a managed-zone, run:

            $ {command} describe my_zone

          To see the list of all managed-zones, run:

            $ {command} list
          """,
  }
