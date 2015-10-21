# Copyright 2014 Google Inc. All Rights Reserved.
"""Commands for reading and manipulating target HTTPS proxies."""

from googlecloudsdk.calliope import base


@base.ReleaseTracks(base.ReleaseTrack.ALPHA, base.ReleaseTrack.BETA)
class TargetHTTPSProxies(base.Group):
  """List, create, and delete target HTTPS proxies."""


TargetHTTPSProxies.detailed_help = {
    'brief': 'List, create, and delete target HTTPS proxies',
}
