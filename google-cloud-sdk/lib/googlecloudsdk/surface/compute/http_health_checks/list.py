# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for listing HTTP health checks."""
from googlecloudsdk.api_lib.compute import base_classes


class List(base_classes.GlobalLister):
  """List HTTP health checks."""

  @property
  def service(self):
    return self.compute.httpHealthChecks

  @property
  def resource_type(self):
    return 'httpHealthChecks'


List.detailed_help = base_classes.GetGlobalListerHelp('health checks')
