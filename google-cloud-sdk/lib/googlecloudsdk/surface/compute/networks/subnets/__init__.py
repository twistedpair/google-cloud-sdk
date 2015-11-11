# Copyright 2015 Google Inc. All Rights Reserved.
"""Commands for reading and manipulating routers."""

from googlecloudsdk.calliope import base


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class Routers(base.Group):
  """List, describe, and delete Google Compute Engine subnetworks."""


Routers.detailed_help = {
    'brief': 'List, describe, and delete Google Compute Engine subnetworks',
}
