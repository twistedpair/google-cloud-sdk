# Copyright 2015 Google Inc. All Rights Reserved.
"""Command for abandoning instances owned by a managed instance group."""
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.shared.compute import base_classes
from googlecloudsdk.shared.compute import utils


class AbandonInstances(base_classes.BaseAsyncMutator):
  """Abandon instances owned by a managed instance group."""

  @staticmethod
  def Args(parser):
    parser.add_argument('name',
                        help='The managed instance group name.')
    parser.add_argument(
        '--instances',
        type=arg_parsers.ArgList(min_length=1),
        action=arg_parsers.FloatingListValuesCatcher(),
        metavar='INSTANCE',
        required=True,
        help='Names of instances to abandon.')
    utils.AddZoneFlag(
        parser,
        resource_type='instance group manager',
        operation_type='abandon instances')

  def method(self):
    return 'AbandonInstances'

  @property
  def service(self):
    return self.compute.instanceGroupManagers

  @property
  def resource_type(self):
    return 'instanceGroupManagers'

  def CreateRequests(self, args):
    zone_ref = self.CreateZonalReference(args.name, args.zone)
    instance_refs = self.CreateZonalReferences(
        args.instances,
        zone_ref.zone,
        resource_type='instances')
    instances = [instance_ref.SelfLink() for instance_ref in instance_refs]
    return [(self.method(),
             self.messages.ComputeInstanceGroupManagersAbandonInstancesRequest(
                 instanceGroupManager=zone_ref.Name(),
                 instanceGroupManagersAbandonInstancesRequest=(
                     self.messages.InstanceGroupManagersAbandonInstancesRequest(
                         instances=instances,
                     )
                 ),
                 project=self.project,
                 zone=zone_ref.zone,
             ),),]


AbandonInstances.detailed_help = {
    'brief': 'Abandon instances owned by a managed instance group.',
    'DESCRIPTION': """
        *{command}* abandons one or more instances from a managed instance
group, thereby reducing the targetSize of the group. Once instances have been
abandoned, the currentSize of the group is automatically reduced as well to
reflect the change.

Abandoning an instance does not delete the underlying virtual machine instances,
but just removes the instances from the instance group. If you would like the
delete the underlying instances, use the delete-instances command instead.
""",
}
