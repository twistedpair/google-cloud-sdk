# Copyright 2015 Google Inc. All Rights Reserved.
"""Command for stopping autoscaling of a managed instance group."""
from googlecloudsdk.shared.compute import base_classes
from googlecloudsdk.shared.compute import managed_instance_groups_utils
from googlecloudsdk.shared.compute import utils


class StopAutoscaling(base_classes.BaseAsyncMutator):
  """Stop autoscaling a managed instance group."""

  @property
  def service(self):
    return self.compute.autoscalers

  @property
  def resource_type(self):
    return 'autoscalers'

  @property
  def method(self):
    return 'Delete'

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'name',
        metavar='NAME',
        completion_resource='compute.instanceGroupManagers',
        help='Managed instance group which will no longer be autoscaled.')
    utils.AddZoneFlag(
        parser, resource_type='resources', operation_type='delete')

  def CreateRequests(self, args):
    igm_ref = self.CreateZonalReference(
        args.name, args.zone, resource_type='instanceGroupManagers')
    # We need the zone name, which might have been passed after prompting.
    # In that case, we get it from the reference.
    zone = args.zone or igm_ref.zone

    managed_instance_groups_utils.AssertInstanceGroupManagerExists(
        igm_ref, self.project, self.messages, self.compute, self.http,
        self.batch_url)

    autoscaler = managed_instance_groups_utils.AutoscalerForMig(
        mig_name=args.name,
        autoscalers=managed_instance_groups_utils.AutoscalersForZones(
            zones=[zone],
            project=self.project,
            compute=self.compute,
            http=self.http,
            batch_url=self.batch_url),
        project=self.project,
        zone=zone)
    if autoscaler is None:
      raise managed_instance_groups_utils.ResourceNotFoundException(
          'The managed instance group is not autoscaled.')
    as_ref = self.CreateZonalReference(autoscaler.name, zone)
    request = self.messages.ComputeAutoscalersDeleteRequest(
        project=self.project)
    request.zone = zone
    request.autoscaler = as_ref.Name()
    return (request,)


StopAutoscaling.detailed_help = {
    'brief': 'Stop autoscaling a managed instance group',
    'DESCRIPTION': """\
        *{command}* stops autoscaling a managed instance group. If autoscaling
is not enabled for the managed instance group, this command does nothing and
will report an error.
""",
}
