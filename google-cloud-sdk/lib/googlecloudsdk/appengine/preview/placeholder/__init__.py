# Copyright 2015 Google Inc. All Rights Reserved.
"""Placeholder command.

Exists because Calliope won't allow empty command groups.
"""
from googlecloudsdk.calliope import base


@base.Hidden
@base.ReleaseTracks(base.ReleaseTrack.GA)
class Placeholder(base.Group):
  """Placeholder command group."""
