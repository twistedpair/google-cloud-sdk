# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for describing firewall rules."""
from googlecloudsdk.shared.compute import base_classes


class Describe(base_classes.GlobalDescriber):
  """Describe a Google Compute Engine firewall rule.

  *{command}* displays all data associated with a Google Compute
  Engine firewall rule in a project.
  """

  @staticmethod
  def Args(parser):
    base_classes.GlobalDescriber.Args(
        parser, 'compute.firewalls', list_command_path='compute.firewall-rules')
    base_classes.AddFieldsFlag(parser, 'firewalls')

  @property
  def service(self):
    return self.compute.firewalls

  @property
  def resource_type(self):
    return 'firewalls'
