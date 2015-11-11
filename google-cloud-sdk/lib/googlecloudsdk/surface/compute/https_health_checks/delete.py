# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for deleting HTTPS health checks."""
from googlecloudsdk.api_lib.compute import base_classes


class Delete(base_classes.GlobalDeleter):
  """Delete HTTPS health checks."""

  @property
  def service(self):
    return self.compute.httpsHealthChecks

  @property
  def resource_type(self):
    return 'httpsHealthChecks'


Delete.detailed_help = {
    'brief': 'Delete HTTPS health checks',
    'DESCRIPTION': """\
        *{command}* deletes one or more Google Compute Engine
        HTTPS health checks.
        """,
}
