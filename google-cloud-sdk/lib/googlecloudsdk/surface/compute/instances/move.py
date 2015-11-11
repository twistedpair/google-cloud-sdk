# Copyright 2015 Google Inc. All Rights Reserved.
"""Command for moving instances."""

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import utils


class Move(base_classes.NoOutputAsyncMutator):
  """Move an instance between zones."""

  @property
  def service(self):
    return self.compute.projects

  @property
  def resource_type(self):
    return 'projects'

  @property
  def method(self):
    return 'MoveInstance'

  @property
  def custom_get_requests(self):
    return self._target_to_get_request

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'name',
        metavar='INSTANCE',
        completion_resource='compute.instances',
        help='The name of the instance to move.')
    parser.add_argument(
        '--destination-zone',
        completion_resource='compute.zones',
        help='The zone to move the instance to.',
        required=True)
    utils.AddZoneFlag(
        parser,
        resource_type='instance',
        operation_type='move')

  def CreateRequests(self, args):
    """Returns a request for moving a instance."""

    target_instance = self.CreateZonalReference(
        args.name, args.zone, resource_type='instances')
    destination_zone = self.CreateGlobalReference(
        args.destination_zone, resource_type='zones')

    request = self.messages.ComputeProjectsMoveInstanceRequest(
        instanceMoveRequest=self.messages.InstanceMoveRequest(
            destinationZone=destination_zone.SelfLink(),
            targetInstance=target_instance.SelfLink(),
        ),
        project=self.project,
    )

    destination_instance_ref = self.CreateZonalReference(
        args.name, args.destination_zone, resource_type='instances')
    project_ref = self.CreateGlobalReference(self.project)

    self._target_to_get_request = {}
    self._target_to_get_request[project_ref.SelfLink()] = (
        destination_instance_ref.SelfLink(),
        self.compute.instances,
        self.messages.ComputeInstancesGetRequest(
            instance=target_instance.Name(),
            project=self.project,
            zone=destination_zone.Name()))

    return [request]


Move.detailed_help = {
    'brief': 'Move an instance between zones',
    'DESCRIPTION': """\
        *{command}* facilitates moving a Google Compute Engine virtual machine
        from one zone to another. Moving a virtual machine may incur downtime
        if the guest OS must be shutdown in order to quiesce disk volumes
        prior to snapshotting.

        For example, running:
           $ gcloud compute instances move example-instance-1 --zone us-central1-b --destination-zone us-central1-f

        will move the instance called example-instance-1, currently running in
        us-central1-b, to us-central1-f.
    """}

