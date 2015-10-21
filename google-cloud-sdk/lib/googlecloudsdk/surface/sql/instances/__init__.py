# Copyright 2013 Google Inc. All Rights Reserved.

"""Provide commands for managing Cloud SQL instances."""

from googlecloudsdk.calliope import base


@base.ReleaseTracks(base.ReleaseTrack.GA, base.ReleaseTrack.BETA)
class Instances(base.Group):
  """Provide commands for managing Cloud SQL instances.

  Provide commands for managing Cloud SQL instances including creating,
  configuring, restarting, and deleting instances.
  """
