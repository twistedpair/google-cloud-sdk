# Copyright 2015 Google Inc. All Rights Reserved.

"""The gcloud emulators command group."""

from googlecloudsdk.calliope import base


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class Emulators(base.Group):
  """Set up your local development environment using emulators."""

  detailed_help = {
      'DESCRIPTION': '{description}',
  }
