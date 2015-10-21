# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for describing target pools."""
from googlecloudsdk.shared.compute import base_classes


class Describe(base_classes.RegionalDescriber):
  """Describe a Google Compute Engine target pool.

  *{command}* displays all data associated with a Google Compute
  Engine target pool in a project.
  """

  @staticmethod
  def Args(parser):
    base_classes.RegionalDescriber.Args(parser, 'compute.targetPools')
    base_classes.AddFieldsFlag(parser, 'targetPools')

  @property
  def service(self):
    return self.compute.targetPools

  @property
  def resource_type(self):
    return 'targetPools'
