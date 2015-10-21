# Copyright 2015 Google Inc. All Rights Reserved.

"""The super-group for the meta commands."""

from googlecloudsdk.calliope import base


@base.Hidden
@base.ReleaseTracks(base.ReleaseTrack.GA)
class Meta(base.Group):
  """Cloud meta introspection commands."""
