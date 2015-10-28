# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for describing networks."""
from googlecloudsdk.api_lib.compute import base_classes


class Describe(base_classes.GlobalDescriber):
  """Describe a Google Compute Engine network."""

  @staticmethod
  def Args(parser):
    base_classes.GlobalDescriber.Args(parser, 'compute.networks')
    base_classes.AddFieldsFlag(parser, 'networks')

  @property
  def service(self):
    return self.compute.networks

  @property
  def resource_type(self):
    return 'networks'


Describe.detailed_help = {
    'brief': 'Describe a Google Compute Engine network',
    'DESCRIPTION': """\
        *{command}* displays all data associated with Google Compute
        Engine network in a project.
        """,
}
