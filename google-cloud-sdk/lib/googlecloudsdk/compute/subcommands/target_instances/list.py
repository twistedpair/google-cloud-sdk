# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for listing target instances."""
from googlecloudsdk.shared.compute import base_classes


class List(base_classes.ZonalLister):
  """List target instances."""

  @property
  def service(self):
    return self.compute.targetInstances

  @property
  def resource_type(self):
    return 'targetInstances'


List.detailed_help = base_classes.GetZonalListerHelp('target instances')
