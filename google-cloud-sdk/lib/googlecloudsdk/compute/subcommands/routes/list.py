# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for listing routes."""
from googlecloudsdk.api_lib.compute import base_classes


class List(base_classes.GlobalLister):
  """List routes."""

  @property
  def service(self):
    return self.compute.routes

  @property
  def resource_type(self):
    return 'routes'


List.detailed_help = base_classes.GetGlobalListerHelp('routes')
