# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for describing vpn tunnels."""
from googlecloudsdk.shared.compute import base_classes


class Describe(base_classes.RegionalDescriber):
  """Describe a vpn tunnel."""

  # Placeholder to indicate that a detailed_help field exists and should
  # be set outside the class definition.
  detailed_help = None

  @staticmethod
  def Args(parser):
    """Adds arguments to the supplied parser."""

    base_classes.RegionalDescriber.Args(parser, 'vpnTunnels')
    base_classes.AddFieldsFlag(parser, 'vpnTunnels')

  @property
  def service(self):
    return self.compute.vpnTunnels

  @property
  def resource_type(self):
    return 'vpnTunnels'


Describe.detailed_help = {
    'brief': 'Describe a Google Compute Engine vpn tunnel',
    'DESCRIPTION': """\
        *{command}* displays all data associated with a Google Compute
        Engine vpn tunnel in a project.
        """,
}
