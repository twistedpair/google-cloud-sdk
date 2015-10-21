# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for listing firewall rules."""
from googlecloudsdk.shared.compute import base_classes


class List(base_classes.GlobalLister):
  """List Google Compute Engine firewall rules."""

  @property
  def service(self):
    return self.compute.firewalls

  @property
  def resource_type(self):
    return 'firewalls'


List.detailed_help = base_classes.GetGlobalListerHelp('firewall rules')
