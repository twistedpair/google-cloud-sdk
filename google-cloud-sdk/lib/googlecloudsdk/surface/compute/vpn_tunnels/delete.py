# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for deleting vpn tunnels."""
from googlecloudsdk.api_lib.compute import base_classes


class Delete(base_classes.RegionalDeleter):
  """Delete vpn tunnels."""

  # Placeholder to indicate that a detailed_help field exists and should
  # be set outside the class definition.
  detailed_help = None

  @property
  def service(self):
    return self.compute.vpnTunnels

  @property
  def resource_type(self):
    return 'vpnTunnels'


Delete.detailed_help = {
    'brief': 'Delete vpn tunnels',
    'DESCRIPTION': """\
        *{command}* deletes one or more Google Compute Engine vpn tunnels.
        """,
}
