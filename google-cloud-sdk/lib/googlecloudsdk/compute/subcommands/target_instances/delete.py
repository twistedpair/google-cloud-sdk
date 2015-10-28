# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for deleting target instances."""
from googlecloudsdk.api_lib.compute import base_classes


class Delete(base_classes.ZonalDeleter):
  """Delete target instances."""

  @staticmethod
  def Args(parser):
    base_classes.ZonalDeleter.Args(parser, 'compute.targetInstances')

  @property
  def service(self):
    return self.compute.targetInstances

  @property
  def resource_type(self):
    return 'targetInstances'


Delete.detailed_help = {
    'brief': 'Delete target instances',
    'DESCRIPTION': """\
        *{command}* deletes one or more Google Compute Engine target
        instances. Target instances can be deleted only if they are
        not being used by any other resources like forwarding rules.
        """,
}
