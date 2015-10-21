# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for listing target pools."""
from googlecloudsdk.shared.compute import base_classes


class List(base_classes.RegionalLister):
  """List target pools."""

  @property
  def service(self):
    return self.compute.targetPools

  @property
  def resource_type(self):
    return 'targetPools'


List.detailed_help = base_classes.GetRegionalListerHelp('target pools')
