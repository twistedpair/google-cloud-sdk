# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for listing SSL certificates."""
from googlecloudsdk.shared.compute import base_classes


class List(base_classes.GlobalLister):
  """List Google Compute Engine SSL certificates."""

  @property
  def service(self):
    return self.compute.sslCertificates

  @property
  def resource_type(self):
    return 'sslCertificates'


List.detailed_help = base_classes.GetGlobalListerHelp('SSL certificates')
