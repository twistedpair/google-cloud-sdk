# Copyright 2014 Google Inc. All Rights Reserved.
"""Commands for reading and manipulating VPN Gateways."""

from googlecloudsdk.calliope import base


class TargetVpnGateways(base.Group):
  """Read and manipulate Google Compute Engine VPN Gateways."""

  # Placeholder to indicate that a detailed_help field exists and should
  # be set outside the class definition.
  detailed_help = None


TargetVpnGateways.detailed_help = {
    'brief': (
        'Read and manipulate Google Compute Engine VPN Gateways'),
}
