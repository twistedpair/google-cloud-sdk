# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for creating unmanaged instance groups."""
from googlecloudsdk.shared.compute import base_classes
from googlecloudsdk.shared.compute import utils
from googlecloudsdk.shared.compute import zone_utils


class Create(base_classes.BaseAsyncCreator, zone_utils.ZoneResourceFetcher):
  """Create Google Compute Engine unmanaged instance groups."""

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--description',
        help=('Specifies a textual description for the '
              'unmanaged instance group.'))

    parser.add_argument(
        'name',
        metavar='NAME',
        help='The name of the unmanaged instance group to create.')

    utils.AddZoneFlag(
        parser,
        resource_type='unmanaged instance group',
        operation_type='create')

  @property
  def service(self):
    return self.compute.instanceGroups

  @property
  def method(self):
    return 'Insert'

  @property
  def resource_type(self):
    return 'instanceGroups'

  def CreateRequests(self, args):
    """Creates and returns an InstanceGroups.Insert request.

    Args:
      args: the argparse arguments that this command was invoked with.

    Returns:
      request: a ComputeInstanceGroupsInsertRequest message object
    """
    group_ref = self.CreateZonalReference(args.name, args.zone)
    self.WarnForZonalCreation([group_ref])

    request = self.messages.ComputeInstanceGroupsInsertRequest(
        instanceGroup=self.messages.InstanceGroup(
            name=group_ref.Name(),
            description=args.description),
        zone=group_ref.zone,
        project=self.project)

    return [request]

Create.detailed_help = {
    'brief': 'Create a Compute Engine unmanaged instance group',
    'DESCRIPTION': """\
        *{command}* creates a new Google Compute Engine unmanaged
        instance group.
        For example:

          $ {command} example-instance-group --zone us-central1-a

        The above example creates one unmanaged instance group called
        'example-instance-group' in the ``us-central1-a'' zone.
        """,
}
