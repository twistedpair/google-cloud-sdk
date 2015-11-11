# Copyright 2015 Google Inc. All Rights Reserved.
"""Command for setting target pools of managed instance group."""

import argparse

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log


class SetTargetPools(base_classes.BaseAsyncMutator):
  """Set target pools of managed instance group."""

  @staticmethod
  def Args(parser):
    parser.add_argument('name', help='Managed instance group name.')
    mutually_exclusive_group = parser.add_mutually_exclusive_group()
    mutually_exclusive_group.add_argument(
        '--clear-target-pools',
        action='store_true',
        help=argparse.SUPPRESS)
    mutually_exclusive_group.add_argument(
        '--target-pools',
        type=arg_parsers.ArgList(min_length=0),
        action=arg_parsers.FloatingListValuesCatcher(),
        metavar='TARGET_POOL',
        help=('Compute Engine Target Pools to add the instances to. '
              'Target Pools must be specified by name or by URL. Example: '
              '--target-pool target-pool-1,target-pool-2.'))
    utils.AddZoneFlag(
        parser,
        resource_type='instance group manager',
        operation_type='set target pools')

  @property
  def method(self):
    return 'SetTargetPools'

  @property
  def service(self):
    return self.compute.instanceGroupManagers

  @property
  def resource_type(self):
    return 'instanceGroupManagers'

  def _ValidateArgs(self, args):
    if not args.clear_target_pools and args.target_pools is None:
      raise exceptions.InvalidArgumentException(
          '--target-pools', 'not passed but --clear-target-pools not present '
          'either.')
    if args.clear_target_pools:
      log.warn('Flag --clear-target-pools is deprecated. Use --target-pools '
               'with empty string ("") as the target pool list instead.')

  def CreateRequests(self, args):
    self._ValidateArgs(args)
    ref = self.CreateZonalReference(args.name, args.zone)
    region = utils.ZoneNameToRegionName(ref.zone)
    if args.clear_target_pools:
      pool_refs = []
    else:
      pool_refs = self.CreateRegionalReferences(
          args.target_pools, region, resource_type='targetPools')
    pools = [pool_ref.SelfLink() for pool_ref in pool_refs]
    request = (
        self.messages.ComputeInstanceGroupManagersSetTargetPoolsRequest(
            instanceGroupManager=ref.Name(),
            instanceGroupManagersSetTargetPoolsRequest=(
                self.messages.InstanceGroupManagersSetTargetPoolsRequest(
                    targetPools=pools,
                )
            ),
            project=self.project,
            zone=ref.zone,)
    )
    return [request]


SetTargetPools.detailed_help = {
    'brief': 'Set instance template for managed instance group.',
    'DESCRIPTION': """
        *{command}* sets the target pools for an existing managed instance group.
Instances that are part of the managed instance group will be added to the
target pool automatically.

Setting a new target pool won't apply to existing instances in the group unless
they are recreated using the recreate-instances command. But any new instances
created in the managed instance group will be added to all of the provided
target pools for load balancing purposes.
""",
}
