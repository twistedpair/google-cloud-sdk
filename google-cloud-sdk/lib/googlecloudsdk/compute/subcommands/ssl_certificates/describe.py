# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for describing SSL certificates."""
from googlecloudsdk.shared.compute import base_classes


class Describe(base_classes.GlobalDescriber):
  """Describe a Google Compute Engine SSL certificate."""

  @staticmethod
  def Args(parser):
    base_classes.GlobalDescriber.Args(parser)
    base_classes.AddFieldsFlag(parser, 'SSL certificates')

  @property
  def service(self):
    return self.compute.sslCertificates

  @property
  def resource_type(self):
    return 'sslCertificates'


Describe.detailed_help = {
    'brief': 'Describe a Google Compute Engine SSL certificate',
    'DESCRIPTION': """\
        *{command}* displays all data associated with Google Compute
        Engine SSL certificate in a project.
        """,
}
