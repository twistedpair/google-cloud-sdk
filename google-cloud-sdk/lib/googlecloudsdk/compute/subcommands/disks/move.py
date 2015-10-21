# Copyright 2015 Google Inc. All Rights Reserved.
"""Command for moving disks."""

from googlecloudsdk.shared.compute import base_classes
from googlecloudsdk.shared.compute import utils


class Move(base_classes.BaseAsyncMutator):
  """Move a disk between zones."""

  @property
  def service(self):
    return self.compute.projects

  @property
  def resource_type(self):
    return 'projects'

  @property
  def method(self):
    return 'MoveDisk'

  @property
  def custom_get_requests(self):
    return self._target_to_get_request

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'name',
        metavar='DISK',
        completion_resource='compute.disks',
        help='The name of the disk to move.')
    parser.add_argument(
        '--destination-zone',
        help='The zone to move the disk to.',
        completion_resource='compute.zones',
        required=True)
    utils.AddZoneFlag(
        parser,
        resource_type='disk',
        operation_type='move')

  def CreateRequests(self, args):
    """Returns a request for moving a disk."""

    target_disk = self.CreateZonalReference(
        args.name, args.zone, resource_type='disks')
    destination_zone = self.CreateGlobalReference(
        args.destination_zone, resource_type='zones')

    request = self.messages.ComputeProjectsMoveDiskRequest(
        diskMoveRequest=self.messages.DiskMoveRequest(
            destinationZone=destination_zone.SelfLink(),
            targetDisk=target_disk.SelfLink(),
        ),
        project=self.project,
    )

    destination_disk_ref = self.CreateZonalReference(
        args.name, args.destination_zone, resource_type='disks')
    project_ref = self.CreateGlobalReference(self.project)

    self._target_to_get_request = {}
    self._target_to_get_request[project_ref.SelfLink()] = (
        destination_disk_ref.SelfLink(),
        self.compute.disks,
        self.messages.ComputeDisksGetRequest(
            disk=target_disk.Name(),
            project=self.project,
            zone=destination_zone.Name()))

    return [request]

Move.detailed_help = {
    'brief': 'Move a disk between zones',
    'DESCRIPTION': """\
        *{command}* facilitates moving a Google Compute Engine disk volume from
        one zone to another. You cannot move a disk if it is attached to a
        running or stopped instance; use the gcloud compute instances move
        command instead.

        For example, running:
           $ gcloud compute disks move example-disk-1 --zone us-central1-b --destination-zone us-central1-f

        will move the disk called example-disk-1, currently running in
        us-central1-b, to us-central1-f.
    """}
