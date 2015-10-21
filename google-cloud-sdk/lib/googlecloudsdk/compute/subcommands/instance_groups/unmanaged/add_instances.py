# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for adding instances to unmanaged instance group."""
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.shared.compute import base_classes
from googlecloudsdk.shared.compute import instance_groups_utils
from googlecloudsdk.shared.compute import utils


class AddInstances(base_classes.NoOutputAsyncMutator):
  """Add instances to an unmanaged instance group."""

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'name',
        help='The name of the unmanaged instance group.')

    parser.add_argument(
        '--instances',
        required=True,
        type=arg_parsers.ArgList(min_length=1),
        action=arg_parsers.FloatingListValuesCatcher(),
        metavar='INSTANCE',
        help='A list of names of instances to add to the instance group. '
        'These must exist beforehand and must live in the same zone as '
        'the instance group.')

    utils.AddZoneFlag(
        parser,
        resource_type='unmanaged instance group',
        operation_type='add instances to')

  @property
  def service(self):
    return self.compute.instanceGroups

  @property
  def method(self):
    return 'AddInstances'

  @property
  def resource_type(self):
    return 'instanceGroups'

  def CreateRequests(self, args):
    group_ref = self.CreateZonalReference(args.name, args.zone)

    instance_references = [
        self.CreateZonalReference(
            instance_name, group_ref.zone, resource_type='instances')
        for instance_name in args.instances]

    instance_groups_utils.ValidateInstanceInZone(instance_references,
                                                 group_ref.zone)
    instance_references = [
        self.messages.InstanceReference(instance=inst.SelfLink())
        for inst in instance_references]
    request_payload = self.messages.InstanceGroupsAddInstancesRequest(
        instances=instance_references)

    request = self.messages.ComputeInstanceGroupsAddInstancesRequest(
        instanceGroup=group_ref.Name(),
        instanceGroupsAddInstancesRequest=request_payload,
        zone=group_ref.zone,
        project=self.context['project']
    )

    return [request]

  detailed_help = {
      'brief': 'Adds instances to an unmanaged instance group by name',
      'DESCRIPTION': """\
          *{command}* adds existing instances to an unmanaged instance group
          by name.
          For example:

            $ {command} example-instance-group \
                --instances example-instance-1 example-instance-2 \
                --zone us-central1-a
          """,
  }
