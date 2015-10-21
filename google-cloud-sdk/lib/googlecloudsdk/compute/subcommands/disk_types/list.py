# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for listing disk types."""
from googlecloudsdk.shared.compute import base_classes


class List(base_classes.ZonalLister):
  """List Google Compute Engine disk types."""

  @property
  def service(self):
    return self.compute.diskTypes

  @property
  def resource_type(self):
    return 'diskTypes'


List.detailed_help = base_classes.GetZonalListerHelp('disk types')
