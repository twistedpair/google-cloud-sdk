# Copyright 2015 Google Inc. All Rights Reserved.
"""Command for setting machine type for virtual machine instances."""

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import instance_utils
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.calliope import base


@base.ReleaseTracks(base.ReleaseTrack.ALPHA, base.ReleaseTrack.BETA)
class SetMachineType(base_classes.NoOutputAsyncMutator):
  """Set machine type for Google Compute Engine virtual machine instances."""

  @staticmethod
  def Args(parser):

    parser.add_argument(
        'name',
        metavar='NAME',
        completion_resource='compute.instances',
        help='The name of the instance to change the machine type for.')

    instance_utils.AddMachineTypeArgs(parser)
    instance_utils.AddCustomMachineTypeArgs(parser)

    utils.AddZoneFlag(
        parser,
        resource_type='instance',
        operation_type='change the machine type for')

  @property
  def service(self):
    return self.compute.instances

  @property
  def method(self):
    return 'SetMachineType'

  @property
  def resource_type(self):
    return 'instances'

  def CreateRequests(self, args):
    """Returns a list of request necessary for setting scheduling options."""
    instance_ref = self.CreateZonalReference(args.name, args.zone)

    machine_type = instance_utils.InterpretMachineType(args)

    instance_utils.CheckCustomCpuRamRatio(self, args.zone, machine_type)

    machine_type_uri = self.CreateZonalReference(
        machine_type, instance_ref.zone,
        resource_type='machineTypes').SelfLink()

    set_machine_type_request = self.messages.InstancesSetMachineTypeRequest(
        machineType=machine_type_uri)
    request = self.messages.ComputeInstancesSetMachineTypeRequest(
        instance=instance_ref.Name(),
        project=self.project,
        instancesSetMachineTypeRequest=set_machine_type_request,
        zone=instance_ref.zone)

    return (request,)


SetMachineType.detailed_help = {
    'brief': 'Set machine type for Google Compute Engine virtual machines',
    'DESCRIPTION': """\
        ``{command}'' allows you to change the machine type of a virtual machine
        in the *TERMINATED* state (that is, a virtual machine instance that
        has been stopped).

        For example, if ``example-instance'' is a ``g1-small'' virtual machine
        currently in the *TERMINATED* state, running:

          $ {command} example-instance --zone us-central1-b --machine-type n1-standard-4

        will change the machine type to ``n1-standard-4'', so that when you
        next start ``example-instance'', it will be provisioned as an
        ``n1-standard-4'' instead of a ``g1-small''.

        See <https://cloud.google.com/compute/docs/machine-types> for more
        information on machine types.
        """,
}
