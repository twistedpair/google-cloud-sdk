# Copyright 2015 Google Inc. All Rights Reserved.

"""Command for describing subnetworks."""
from googlecloudsdk.api_lib.compute import base_classes


class Describe(base_classes.RegionalDescriber):
  """Describe a Google Compute Engine subnetwork.

  *{command}* displays all data associated with a Google Compute
  Engine subnetwork.
  """

  @staticmethod
  def Args(parser):
    base_classes.RegionalDescriber.Args(parser, 'compute.subnetworks')
    base_classes.AddFieldsFlag(parser, 'subnetworks')

  @property
  def service(self):
    return self.compute.subnetworks

  @property
  def resource_type(self):
    return 'subnetworks'
