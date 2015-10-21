# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for deleting target vpn gateways."""
from googlecloudsdk.shared.compute import base_classes


class Delete(base_classes.RegionalDeleter):
  """Delete target vpn gateways."""

  # Placeholder to indicate that a detailed_help field exists and should
  # be set outside the class definition.
  detailed_help = None

  @property
  def service(self):
    return self.compute.targetVpnGateways

  @property
  def resource_type(self):
    return 'targetVpnGateways'


Delete.detailed_help = {
    'brief': 'Delete target vpn gateways',
    'DESCRIPTION': """\
        *{command}* deletes one or more Google Compute Engine target vpn
        gateways.
        """,
}
