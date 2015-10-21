# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for listing instance templates."""
from googlecloudsdk.shared.compute import base_classes


class List(base_classes.GlobalLister):
  """List Google Compute Engine virtual machine instance templates."""

  @property
  def service(self):
    return self.compute.instanceTemplates

  @property
  def resource_type(self):
    return 'instanceTemplates'


List.detailed_help = base_classes.GetZonalListerHelp('instance tempates')
