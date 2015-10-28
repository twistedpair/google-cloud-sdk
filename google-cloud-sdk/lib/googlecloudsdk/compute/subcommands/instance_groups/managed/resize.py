# Copyright 2015 Google Inc. All Rights Reserved.
"""Command for setting size of managed instance group."""
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import utils


class Resize(base_classes.BaseAsyncMutator):
  """Set managed instance group size."""

  @staticmethod
  def Args(parser):
    parser.add_argument('name', help='Managed instance group name.')
    parser.add_argument(
        '--size',
        required=True,
        type=int,
        help=('Target number of instances in managed instance group.'))
    utils.AddZoneFlag(
        parser,
        resource_type='instance group manager',
        operation_type='resize')

  def method(self):
    return 'Resize'

  @property
  def service(self):
    return self.compute.instanceGroupManagers

  @property
  def resource_type(self):
    return 'instanceGroupManagers'

  def CreateRequests(self, args):
    ref = self.CreateZonalReference(args.name, args.zone)
    return [(self.method(),
             self.messages.ComputeInstanceGroupManagersResizeRequest(
                 instanceGroupManager=ref.Name(),
                 size=args.size,
                 project=self.project,
                 zone=ref.zone,))]


Resize.detailed_help = {
    'brief': 'Set managed instance group size.',
    'DESCRIPTION': """
        *{command}* resize a managed instance group to a provided size.

If you resize down, the Instance Group Manager service deletes instances from
the group until the group reaches the desired size. To understand in what order
instances will be deleted, see the API documentation.

If you resize up, the service adds instances to the group using the current
instance template until the group reaches the desired size.
""",
}
