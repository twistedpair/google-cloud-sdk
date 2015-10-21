# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for describing disk types."""
from googlecloudsdk.shared.compute import base_classes


class Describe(base_classes.ZonalDescriber):
  """Describe a Google Compute Engine disk type."""

  @staticmethod
  def Args(parser):
    base_classes.ZonalDescriber.Args(parser, 'compute.diskTypes')
    base_classes.AddFieldsFlag(parser, 'diskTypes')

  @property
  def service(self):
    return self.compute.diskTypes

  @property
  def resource_type(self):
    return 'diskTypes'


Describe.detailed_help = {
    'brief': 'Describe a Google Compute Engine disk type',
    'DESCRIPTION': """\
        *{command}* displays all data associated with a Google Compute
        Engine disk type.
        """,
}
