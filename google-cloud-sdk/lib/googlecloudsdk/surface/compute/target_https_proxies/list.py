# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for listing target HTTPS proxies."""
from googlecloudsdk.api_lib.compute import base_classes


class List(base_classes.GlobalLister):
  """List target HTTPS proxies."""

  @property
  def service(self):
    return self.compute.targetHttpsProxies

  @property
  def resource_type(self):
    return 'targetHttpsProxies'


List.detailed_help = base_classes.GetGlobalListerHelp('target HTTPS proxies')
