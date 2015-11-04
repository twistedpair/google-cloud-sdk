# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for listing networks."""

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import networks_utils


class List(base_classes.GlobalLister):
  """List Google Compute Engine networks."""

  @property
  def service(self):
    return self.compute.networks

  @property
  def resource_type(self):
    return 'networks'

  def ComputeDynamicProperties(self, args, items):
    return networks_utils.AddMode(items)


List.detailed_help = base_classes.GetZonalListerHelp('networks')
