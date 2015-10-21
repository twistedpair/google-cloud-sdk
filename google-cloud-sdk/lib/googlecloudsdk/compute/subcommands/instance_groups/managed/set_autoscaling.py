# Copyright 2015 Google Inc. All Rights Reserved.
"""Command for configuring autoscaling of a managed instance group."""
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.shared.compute import base_classes
from googlecloudsdk.shared.compute import managed_instance_groups_utils
from googlecloudsdk.shared.compute import utils


class SetAutoscaling(base_classes.BaseAsyncMutator):
  """Set autoscaling parameters of a managed instance group."""

  _method = None

  @property
  def service(self):
    return self.compute.autoscalers

  @property
  def resource_type(self):
    return 'autoscalers'

  @property
  def method(self):
    if self._method is None:
      raise exceptions.ToolException(
          'Internal error: attempted calling method before determining which '
          'method to call.')
    return self._method

  @staticmethod
  def Args(parser):
    managed_instance_groups_utils.AddAutoscalerArgs(parser)
    parser.add_argument(
        'name',
        metavar='NAME',
        completion_resource='compute.instanceGroupManagers',
        help='Managed instance group which autoscaling parameters will be set.')
    utils.AddZoneFlag(
        parser, resource_type='resources', operation_type='update')

  def CreateRequests(self, args):
    managed_instance_groups_utils.ValidateAutoscalerArgs(args)

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
        zone=zone,
        project=self.project)
    autoscaler_name = getattr(autoscaler, 'name', None)
    as_ref = self.CreateZonalReference(autoscaler_name or args.name, zone)
    autoscaler_resource = managed_instance_groups_utils.BuildAutoscaler(
        args, self.messages, as_ref, igm_ref)

    if autoscaler_name is None:
      self._method = 'Insert'
      request = self.messages.ComputeAutoscalersInsertRequest(
          project=self.project)
      managed_instance_groups_utils.AdjustAutoscalerNameForCreation(
          autoscaler_resource)
      request.autoscaler = autoscaler_resource
    else:
      self._method = 'Update'
      request = self.messages.ComputeAutoscalersUpdateRequest(
          project=self.project)
      request.autoscaler = as_ref.Name()
      request.autoscalerResource = autoscaler_resource

    request.zone = as_ref.zone
    return (request,)


SetAutoscaling.detailed_help = {
    'brief': 'Set autoscaling parameters of a managed instance group',
    'DESCRIPTION': """\
        *{command}* sets autoscaling parameters of specified managed instance
group.
        """,
}
