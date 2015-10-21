# Copyright 2013 Google Inc. All Rights Reserved.

"""Provide a command to list flags."""


from googlecloudsdk.calliope import base


@base.ReleaseTracks(base.ReleaseTrack.GA, base.ReleaseTrack.BETA)
class Flags(base.Group):
  """Provide a command to list flags."""
