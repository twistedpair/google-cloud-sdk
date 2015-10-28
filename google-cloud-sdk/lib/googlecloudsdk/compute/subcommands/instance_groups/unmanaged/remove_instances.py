# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for removing instances from unmanaged instance groups."""

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import instance_groups_utils
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.calliope import arg_parsers


class RemoveInstances(base_classes.NoOutputAsyncMutator):
  """Removes instances from unmanaged instance group."""

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
        help='The names of the instances to remove from the instance group.')

    utils.AddZoneFlag(
        parser,
        resource_type='unmanaged instance group',
        operation_type='remove instances from')

  @property
  def service(self):
    return self.compute.instanceGroups

  @property
  def method(self):
    return 'RemoveInstances'

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
    request_payload = self.messages.InstanceGroupsRemoveInstancesRequest(
        instances=instance_references)

    request = self.messages.ComputeInstanceGroupsRemoveInstancesRequest(
        instanceGroup=group_ref.Name(),
        instanceGroupsRemoveInstancesRequest=request_payload,
        zone=group_ref.zone,
        project=self.context['project']
    )

    return [request]

  detailed_help = {
      'brief': ('Removes resources from an unmanaged instance group '
                'by instance name'),
      'DESCRIPTION': """\
          *{command}* removes instances from an unmanaged instance group using
          the instance name.

          This does not delete the actual instance resources but removes
          it from the instance group.
          """,
  }
