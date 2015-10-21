# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for deleting routes."""
from googlecloudsdk.shared.compute import base_classes


class Delete(base_classes.GlobalDeleter):
  """Delete routes."""

  @staticmethod
  def Args(parser):
    base_classes.GlobalDeleter.Args(parser, 'compute.routes')

  @property
  def service(self):
    return self.compute.routes

  @property
  def resource_type(self):
    return 'routes'


Delete.detailed_help = {
    'brief': 'Delete routes',
    'DESCRIPTION': """\
        *{command}* deletes one or more Google Compute Engine routes.
        """,
}
