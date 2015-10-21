# Copyright 2014 Google Inc. All Rights Reserved.
"""Commands for reading and manipulating HTTPS health checks."""
from googlecloudsdk.calliope import base


@base.ReleaseTracks(base.ReleaseTrack.ALPHA, base.ReleaseTrack.BETA)
class HttpsHealthChecks(base.Group):
  """Read and manipulate HTTPS health checks for load balanced instances."""


HttpsHealthChecks.detailed_help = {
    'brief': ('Read and manipulate HTTPS health checks for load balanced '
              'instances')
}
