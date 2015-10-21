# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for listing backend services."""
from googlecloudsdk.shared.compute import base_classes


class List(base_classes.GlobalLister):
  """List backend services."""

  @property
  def service(self):
    return self.compute.backendServices

  @property
  def resource_type(self):
    return 'backendServices'


List.detailed_help = base_classes.GetGlobalListerHelp('backend services')
