# Copyright 2015 Google Inc. All Rights Reserved.

"""Command for listing routers."""
from googlecloudsdk.shared.compute import base_classes


class List(base_classes.RegionalLister):
  """List routers."""

  @property
  def service(self):
    return self.compute.routers

  @property
  def resource_type(self):
    return 'routers'


List.detailed_help = base_classes.GetRegionalListerHelp('routers')
