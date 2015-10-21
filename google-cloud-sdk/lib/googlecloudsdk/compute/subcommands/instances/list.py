# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for listing instances."""
from googlecloudsdk.shared.compute import base_classes


class List(base_classes.ZonalLister):
  """List Google Compute Engine virtual machine instances."""

  @property
  def service(self):
    return self.compute.instances

  @property
  def resource_type(self):
    return 'instances'


List.detailed_help = base_classes.GetZonalListerHelp('instances')
