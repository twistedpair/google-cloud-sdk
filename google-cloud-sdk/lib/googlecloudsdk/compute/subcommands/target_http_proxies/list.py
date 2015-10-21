# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for listing target HTTP proxies."""
from googlecloudsdk.shared.compute import base_classes


class List(base_classes.GlobalLister):
  """List target HTTP proxies."""

  @property
  def service(self):
    return self.compute.targetHttpProxies

  @property
  def resource_type(self):
    return 'targetHttpProxies'


List.detailed_help = base_classes.GetGlobalListerHelp('target HTTP proxies')
