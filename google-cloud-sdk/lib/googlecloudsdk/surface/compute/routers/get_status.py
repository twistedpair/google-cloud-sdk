# Copyright 2015 Google Inc. All Rights Reserved.

"""Command for getting the status of routers."""
from googlecloudsdk.api_lib.compute import base_classes


class Describe(base_classes.RegionalDescriber):
  """Get status of a Google Compute Engine router.

  *{command}* displays all runtime data associated with a Google Compute
  Engine router.
  """

  @staticmethod
  def Args(parser):
    # TODO(b/24898638): autocomplete
    # cli = Describe.GetCLIGenerator()
    base_classes.RegionalDescriber.Args(parser, 'compute.routers')
    base_classes.AddFieldsFlag(parser, 'routers')

  @property
  def service(self):
    return self.compute.routers

  @property
  def resource_type(self):
    return 'routers'

  @property
  def method(self):
    return 'GetRouterStatus'
