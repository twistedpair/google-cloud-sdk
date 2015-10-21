# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for describing regions."""
from googlecloudsdk.shared.compute import base_classes


class Describe(base_classes.GlobalDescriber):
  """Describe a Google Compute Engine region."""

  @staticmethod
  def Args(parser):
    base_classes.GlobalDescriber.Args(parser, 'compute.regions')
    base_classes.AddFieldsFlag(parser, 'regions')

  @property
  def service(self):
    return self.compute.regions

  @property
  def resource_type(self):
    return 'regions'


Describe.detailed_help = {
    'brief': 'Describe a Google Compute Engine region',
    'DESCRIPTION': """\
        *{command}* displays all data associated with a Google Compute
        Engine region.
        """,
}
