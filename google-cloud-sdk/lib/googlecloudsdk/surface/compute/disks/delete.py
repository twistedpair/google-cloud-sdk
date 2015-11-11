# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for deleting disks."""
from googlecloudsdk.api_lib.compute import base_classes


class Delete(base_classes.ZonalDeleter):
  """Delete Google Compute Engine persistent disks.

  *{command}* deletes one or more Google Compute Engine
  persistent disks. Disks can be deleted only if they are not
  being used by any virtual machine instances.
  """

  @property
  def service(self):
    return self.compute.disks

  @property
  def resource_type(self):
    return 'disks'

  @property
  def custom_prompt(self):
    return ('The following disks will be deleted. Deleting a disk is '
            'irreversible and any data on the disk will be lost.')

  @staticmethod
  def Args(parser):
    base_classes.ZonalDeleter.Args(parser, 'compute.disks')
