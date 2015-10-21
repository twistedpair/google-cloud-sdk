# Copyright 2015 Google Inc. All Rights Reserved.
"""Command for recreating instances managed by a managed instance group."""
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.shared.compute import base_classes
from googlecloudsdk.shared.compute import utils


class RecreateInstances(base_classes.BaseAsyncMutator):
  """Recreate instances managed by a managed instance group."""

  @staticmethod
  def Args(parser):
    parser.add_argument('name',
                        help='Managed instance group name.')
    parser.add_argument(
        '--instances',
        type=arg_parsers.ArgList(min_length=1),
        action=arg_parsers.FloatingListValuesCatcher(),
        metavar='INSTANCE',
        required=True,
        help='Names of instances to recreate.')
    utils.AddZoneFlag(
        parser,
        resource_type='instance group manager',
        operation_type='recreate instances')

  def method(self):
    return 'RecreateInstances'

  @property
  def service(self):
    return self.compute.instanceGroupManagers

  @property
  def resource_type(self):
    return 'instanceGroupManagers'

  def CreateRequests(self, args):
    zone_ref = self.CreateZonalReference(args.name, args.zone)
    instances_ref = self.CreateZonalReferences(args.instances,
                                               zone_ref.zone,
                                               resource_type='instances')
    instances = [instance_ref.SelfLink() for instance_ref in instances_ref]
    return [(self.method(),
             self.messages.ComputeInstanceGroupManagersRecreateInstancesRequest(
                 instanceGroupManager=zone_ref.Name(),
                 instanceGroupManagersRecreateInstancesRequest=(
                     self.messages.
                     InstanceGroupManagersRecreateInstancesRequest(
                         instances=instances,
                     )
                 ),
                 project=self.project,
                 zone=zone_ref.zone,
             ),),]


RecreateInstances.detailed_help = {
    'brief': 'Recreate instances managed by a managed instance group.',
    'DESCRIPTION': """
        *{command}* is used to recreate one or more instances in a managed
instance group. The underlying virtual machine instances are deleted and
recreated based on the latest instance template configured for the managed
instance group.
""",
}
