# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for deleting unmanaged instance groups."""
from googlecloudsdk.api_lib.compute import base_classes


class Delete(base_classes.ZonalDeleter):
  """Delete Google Compute Engine unmanaged instance groups."""

  @property
  def service(self):
    return self.compute.instanceGroups

  @property
  def resource_type(self):
    return 'instanceGroups'


Delete.detailed_help = {
    'brief': 'Delete Google Compute Engine unmanaged instance groups',
    'DESCRIPTION': """\
        *{command}* deletes one or more Google Compute Engine unmanaged
        instance groups. This command just deletes the instance group and does
        not delete the individual virtual machine instances
        in the instance group.
        For example:

          $ {command} example-instance-group-1 \
              example-instance-group-2 \
              --zone us-central1-a

        The above example deletes two instance groups, example-instance-group-1
        and example-instance-group-2, in the ``us-central1-a'' zone.
        """,
}
