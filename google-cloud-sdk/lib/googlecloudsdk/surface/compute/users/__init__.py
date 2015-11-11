# Copyright 2015 Google Inc. All Rights Reserved.
"""Commands for reading and manipulating users."""

from googlecloudsdk.calliope import base


@base.ReleaseTracks(base.ReleaseTrack.ALPHA, base.ReleaseTrack.BETA)
class Users(base.Group):
  """Read and manipulate Google Compute Engine users."""

Users.detailed_help = {
    'brief': 'Read and manipulate Google Compute Engine users',
}
