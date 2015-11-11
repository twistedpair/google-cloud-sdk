# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for deleting firewall rules."""
from googlecloudsdk.api_lib.compute import base_classes


class Delete(base_classes.GlobalDeleter):
  """Delete Google Compute Engine firewall rules."""

  @staticmethod
  def Args(parser):
    base_classes.GlobalDeleter.Args(parser, 'compute.firewalls',
                                    command='compute.firewall-rules')

  @property
  def service(self):
    return self.compute.firewalls

  @property
  def resource_type(self):
    return 'firewalls'


Delete.detailed_help = {
    'brief': 'Delete Google Compute Engine firewall rules',
    'DESCRIPTION': """\
        *{command}* deletes one or more Google Compute Engine firewall
         rules.
        """,
}
