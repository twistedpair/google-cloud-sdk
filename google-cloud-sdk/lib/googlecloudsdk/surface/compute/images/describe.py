# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for describing images."""
from googlecloudsdk.api_lib.compute import base_classes


class Describe(base_classes.GlobalDescriber):
  """Describe a Google Compute Engine image."""

  @staticmethod
  def Args(parser):
    base_classes.GlobalDescriber.Args(parser, 'compute.images')
    base_classes.AddFieldsFlag(parser, 'images')

  @property
  def service(self):
    return self.compute.images

  @property
  def resource_type(self):
    return 'images'


Describe.detailed_help = {
    'brief': 'Describe a Google Compute Engine image',
    'DESCRIPTION': """\
        *{command}* displays all data associated with a Google Compute
        Engine image in a project.
        """,
}
