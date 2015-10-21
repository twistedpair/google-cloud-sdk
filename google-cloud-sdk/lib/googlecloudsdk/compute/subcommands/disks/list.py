# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for listing persistent disks."""
from googlecloudsdk.shared.compute import base_classes


class List(base_classes.ZonalLister):
  """List Google Compute Engine persistent disks."""

  @property
  def service(self):
    return self.compute.disks

  @property
  def resource_type(self):
    return 'disks'


List.detailed_help = base_classes.GetZonalListerHelp('disks')
