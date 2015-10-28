# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for listing URL maps."""
from googlecloudsdk.api_lib.compute import base_classes


class List(base_classes.GlobalLister):
  """List URL maps."""

  @property
  def service(self):
    return self.compute.urlMaps

  @property
  def resource_type(self):
    return 'urlMaps'


List.detailed_help = base_classes.GetGlobalListerHelp('URL maps')
