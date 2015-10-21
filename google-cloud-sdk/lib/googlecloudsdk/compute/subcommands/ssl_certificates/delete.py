# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for deleting SSL certificates."""
from googlecloudsdk.shared.compute import base_classes


class Delete(base_classes.GlobalDeleter):
  """Delete Google Compute Engine SSL certificates."""

  @property
  def service(self):
    return self.compute.sslCertificates

  @property
  def resource_type(self):
    return 'sslCertificates'


Delete.detailed_help = {
    'brief': 'Delete Google Compute Engine SSL certificates',
    'DESCRIPTION': """\
        *{command}* deletes one or more Google Compute Engine SSL certificates.
        SSL certificates can only be deleted when no other resources (e.g.,
        target HTTPS proxies) refer to them.
        """,
}
