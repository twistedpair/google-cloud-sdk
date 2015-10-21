# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for describing HTTPS health checks."""
from googlecloudsdk.shared.compute import base_classes


class Describe(base_classes.GlobalDescriber):
  """Display detailed information about an HTTPS health check."""

  @staticmethod
  def Args(parser):
    base_classes.GlobalDescriber.Args(parser)
    base_classes.AddFieldsFlag(parser, 'httpsHealthChecks')

  @property
  def service(self):
    return self.compute.httpsHealthChecks

  @property
  def resource_type(self):
    return 'httpsHealthChecks'


Describe.detailed_help = {
    'brief': 'Display detailed information about an HTTPS health check',
    'DESCRIPTION': """\
        *{command}* displays all data associated with a Google Compute
        Engine HTTPS health check in a project.
        """,
}
