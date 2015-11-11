# Copyright 2015 Google Inc. All Rights Reserved.
"""Command for deleting subnetworks."""

from googlecloudsdk.api_lib.compute import base_classes


class Delete(base_classes.RegionalDeleter):
  """Delete Google Compute Engine subnetworks."""

  @staticmethod
  def Args(parser):
    base_classes.RegionalDeleter.Args(parser, 'compute.subnetworks')

  @property
  def service(self):
    return self.compute.subnetworks

  @property
  def resource_type(self):
    return 'subnetworks'


Delete.detailed_help = {
    'brief': 'Delete Google Compute Engine subnetworks',
    'DESCRIPTION': """\
        *{command}* deletes one or more Google Compute Engine
        subnetworks. Subnetworks can only be deleted when no other resources
        (e.g., virtual machine instances) refer to them.
        """,
}
