# Copyright 2015 Google Inc. All Rights Reserved.

"""The snapshot command group for the gcloud source command."""

from googlecloudsdk.calliope import base


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
@base.Hidden
class Snapshot(base.Group):
  """Cloud source snapshot commands."""
