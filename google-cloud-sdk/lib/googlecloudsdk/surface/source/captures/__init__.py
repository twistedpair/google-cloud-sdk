# Copyright 2015 Google Inc. All Rights Reserved.

"""The capture command group for the gcloud source command."""

from googlecloudsdk.calliope import base


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
@base.Hidden
class Capture(base.Group):
  """Cloud source capture commands."""
