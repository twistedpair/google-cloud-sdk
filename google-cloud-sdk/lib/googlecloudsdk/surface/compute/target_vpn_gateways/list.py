# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for listing target VPN gateways."""
from googlecloudsdk.api_lib.compute import base_classes


class List(base_classes.RegionalLister):
  """List target VPN gateways."""

  # Placeholder to indicate that a detailed_help field exists and should
  # be set outside the class definition.
  detailed_help = None

  @property
  def service(self):
    return self.compute.targetVpnGateways

  @property
  def resource_type(self):
    return 'targetVpnGateways'


List.detailed_help = base_classes.GetRegionalListerHelp('target VPN gateways')
