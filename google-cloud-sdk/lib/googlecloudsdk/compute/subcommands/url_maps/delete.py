# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for deleting URL maps."""
from googlecloudsdk.api_lib.compute import base_classes


class Delete(base_classes.GlobalDeleter):
  """Delete URL maps.

  *{command}* deletes one or more URL maps.
  """

  @staticmethod
  def Args(parser):
    base_classes.GlobalDeleter.Args(parser, 'compute.urlMaps')

  @property
  def service(self):
    return self.compute.urlMaps

  @property
  def resource_type(self):
    return 'urlMaps'
