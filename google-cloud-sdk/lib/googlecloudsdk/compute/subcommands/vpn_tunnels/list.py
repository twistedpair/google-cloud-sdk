# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for listing VPN tunnels."""
from googlecloudsdk.api_lib.compute import base_classes


class List(base_classes.RegionalLister):
  """List VPN tunnels."""

  # Placeholder to indicate that a detailed_help field exists and should
  # be set outside the class definition.
  detailed_help = None

  @property
  def service(self):
    return self.compute.vpnTunnels

  @property
  def resource_type(self):
    return 'vpnTunnels'


List.detailed_help = base_classes.GetRegionalListerHelp('VPN tunnels')
