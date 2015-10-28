# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for describing target vpn gateways."""
from googlecloudsdk.api_lib.compute import base_classes


class Describe(base_classes.RegionalDescriber):
  """Describe a target vpn gateway."""

  # Placeholder to indicate that a detailed_help field exists and should
  # be set outside the class definition.
  detailed_help = None

  @staticmethod
  def Args(parser):
    """Adds arguments to the supplied parser."""

    base_classes.RegionalDescriber.Args(parser)
    base_classes.AddFieldsFlag(parser, 'targetVpnGateways')

  @property
  def service(self):
    return self.compute.targetVpnGateways

  @property
  def resource_type(self):
    return 'targetVpnGateways'


Describe.detailed_help = {
    'brief': 'Describe a Google Compute Engine target vpn gateway',
    'DESCRIPTION': """\
        *{command}* displays all data associated with a Google Compute
        Engine target vpn gateway in a project.
        """,
}
