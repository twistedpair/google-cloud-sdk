# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for deleting backend services."""
from googlecloudsdk.api_lib.compute import base_classes


class Delete(base_classes.GlobalDeleter):
  """Delete backend services.

    *{command}* deletes one or more backend services.
  """

  @staticmethod
  def Args(parser):
    base_classes.GlobalDeleter.Args(parser, 'compute.backendServices')

  @property
  def service(self):
    return self.compute.backendServices

  @property
  def resource_type(self):
    return 'backendServices'
