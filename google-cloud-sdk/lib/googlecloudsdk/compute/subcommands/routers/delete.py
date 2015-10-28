# Copyright 2015 Google Inc. All Rights Reserved.

"""Command for deleting routers."""
from googlecloudsdk.api_lib.compute import base_classes


class Delete(base_classes.RegionalDeleter):
  """Delete Google Compute Engine routers."""

  @staticmethod
  def Args(parser):
    cli = Delete.GetCLIGenerator()
    base_classes.RegionalDeleter.Args(parser, 'compute.routers', cli)

  @property
  def service(self):
    return self.compute.routers

  @property
  def resource_type(self):
    return 'routers'


Delete.detailed_help = {
    'brief': 'Delete Google Compute Engine routers',
    'DESCRIPTION': """\
        *{command}* deletes one or more Google Compute Engine
        routers. Routers can only be deleted when no other resources
        (e.g., virtual machine instances) refer to them.
        """,
}
