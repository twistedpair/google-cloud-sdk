# Copyright 2015 Google Inc. All Rights Reserved.
"""Command for creating managed instance group."""

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import managed_instance_groups_utils
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.api_lib.compute import zone_utils
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base


@base.ReleaseTracks(base.ReleaseTrack.GA)
class CreateGA(base_classes.BaseAsyncCreator, zone_utils.ZoneResourceFetcher):
  """Create Google Compute Engine managed instance groups."""

  @staticmethod
  def Args(parser):
    parser.add_argument('name', help='Managed instance group name.')
    parser.add_argument(
        '--template',
        required=True,
        help=('Specifies the instance template to use when creating new '
              'instances.'))
    parser.add_argument(
        '--base-instance-name',
        required=True,
        help=('The base name to use for the Compute Engine instances that will '
              'be created with the managed instance group.'))
    parser.add_argument(
        '--size',
        required=True,
        help=('The initial number of instances you want in this group.'))
    parser.add_argument(
        '--description',
        help='An optional description for this group.')
    parser.add_argument(
        '--target-pool',
        type=arg_parsers.ArgList(),
        action=arg_parsers.FloatingListValuesCatcher(),
        metavar='TARGET_POOL',
        help=('Specifies any target pools you want the instances of this '
              'managed instance group to be part of.'))
    utils.AddZoneFlag(
        parser,
        resource_type='instance group manager',
        operation_type='create')

  @property
  def service(self):
    return self.compute.instanceGroupManagers

  @property
  def method(self):
    return 'Insert'

  @property
  def resource_type(self):
    return 'instanceGroupManagers'

  def CreateRequests(self, args):
    """Creates and returns an instanceGroupManagers.Insert request.

    Args:
      args: the argparse arguments that this command was invoked with.

    Returns:
      request: a singleton list containing
               ComputeManagedInstanceGroupsInsertRequest message object.
    """
    group_ref = self.CreateZonalReference(args.name, args.zone)
    self.WarnForZonalCreation([group_ref])
    template_ref = self.CreateGlobalReference(args.template,
                                              resource_type='instanceTemplates')
    if args.target_pool:
      region = utils.ZoneNameToRegionName(group_ref.zone)
      pool_refs = self.CreateRegionalReferences(
          args.target_pool, region, resource_type='targetPools')
      pools = [pool_ref.SelfLink() for pool_ref in pool_refs]
    else:
      pools = []

    instance_group_manager = self.messages.InstanceGroupManager(
        name=group_ref.Name(),
        zone=group_ref.zone,
        baseInstanceName=args.base_instance_name,
        description=args.description,
        instanceTemplate=template_ref.SelfLink(),
        targetPools=pools,
        targetSize=int(args.size))
    auto_healing_policies = (
        managed_instance_groups_utils.CreateAutohealingPolicies(self, args))
    if auto_healing_policies:
      instance_group_manager.autoHealingPolicies = auto_healing_policies
    request = self.messages.ComputeInstanceGroupManagersInsertRequest(
        instanceGroupManager=instance_group_manager,
        project=self.project,
        zone=group_ref.zone)

    return [request]


@base.ReleaseTracks(base.ReleaseTrack.ALPHA, base.ReleaseTrack.BETA)
class CreateAlphaBeta(CreateGA):
  """Create Google Compute Engine managed instance groups."""

  @staticmethod
  def Args(parser):
    CreateGA.Args(parser)
    # TODO(user, b/22996767): Change "help_hidden" to False after beta launch.
    managed_instance_groups_utils.AddAutohealingArgs(parser, help_hidden=True)


DETAILED_HELP = {
    'brief': 'Create a Compute Engine managed instance group',
    'DESCRIPTION': """\
        *{command}* creates a Google Compute Engine managed instance group.

For example, running:

        $ {command} example-managed-instance-group --zone us-central1-a

will create one managed instance group called 'example-managed-instance-group'
in the ``us-central1-a'' zone.
""",
}
CreateGA.detailed_help = DETAILED_HELP
CreateAlphaBeta.detailed_help = DETAILED_HELP

