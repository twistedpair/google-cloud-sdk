# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for listing HTTPS health checks."""
from googlecloudsdk.shared.compute import base_classes


class List(base_classes.GlobalLister):
  """List HTTPS health checks."""

  @property
  def service(self):
    return self.compute.httpsHealthChecks

  @property
  def resource_type(self):
    return 'httpsHealthChecks'


List.detailed_help = base_classes.GetGlobalListerHelp('HTTPS health checks')
