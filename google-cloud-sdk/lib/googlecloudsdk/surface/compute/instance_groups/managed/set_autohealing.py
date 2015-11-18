# Copyright 2015 Google Inc. All Rights Reserved.
"""Command for setting autohealing policy of managed instance group."""

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import managed_instance_groups_utils
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.calliope import base


@base.ReleaseTracks(base.ReleaseTrack.ALPHA, base.ReleaseTrack.BETA)
class SetAutohealing(base_classes.BaseAsyncMutator):
  """Set autohealing policy of instance group manager."""

  @staticmethod
  def Args(parser):
    parser.add_argument('name', help='Managed instance group name.')
    managed_instance_groups_utils.AddAutohealingArgs(parser)
    utils.AddZoneFlag(
        parser,
        resource_type='instance group manager',
        operation_type='set autohealing policy')

  @property
  def method(self):
    return 'SetAutoHealingPolicies'

  @property
  def service(self):
    return self.compute.instanceGroupManagers

  @property
  def resource_type(self):
    return 'instanceGroupManagers'

  def CreateRequests(self, args):
    ref = self.CreateZonalReference(args.name, args.zone)
    auto_healing_policies = (
        managed_instance_groups_utils.CreateAutohealingPolicies(self, args))
    request = (
        self.messages.ComputeInstanceGroupManagersSetAutoHealingPoliciesRequest(
            project=self.project,
            zone=ref.zone,
            instanceGroupManager=ref.Name(),
            instanceGroupManagersSetAutoHealingRequest=(
                self.messages.InstanceGroupManagersSetAutoHealingRequest(
                    autoHealingPolicies=auto_healing_policies)))
    )
    return [request]


SetAutohealing.detailed_help = {
    'brief': 'Set autohealing policy for managed instance group.',
    'DESCRIPTION': """
        *{command}* updates the autohealing policy for an existing managed
instance group.

If --http-health-check or --https-health-check is specified, the resulting
autohealing policy will be triggered by the health-check i.e. the autohealing
action (RECREATE) on an instance will be performed if the health-check signals
that the instance is UNHEALTHY. If neither --http-health-check nor
--https-health-check is specified, the resulting autohealing policy will be
triggered by instance's status i.e. the autohealing action (RECREATE) on an
instance will be performed if the instance.status is not RUNNING.
--initial-delay specifies the length of the period during which IGM will
refrain from autohealing the instance even if the instance is reported as not
RUNNING or UNHEALTHY.
""",
}
