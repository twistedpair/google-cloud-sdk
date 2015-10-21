# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for listing networks."""
from googlecloudsdk.shared.compute import base_classes


class List(base_classes.GlobalLister):
  """List Google Compute Engine networks."""

  @property
  def service(self):
    return self.compute.networks

  @property
  def resource_type(self):
    return 'networks'


List.detailed_help = base_classes.GetZonalListerHelp('networks')
