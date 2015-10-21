# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for listing instance groups."""
from googlecloudsdk.shared.compute import base_classes


class List(base_classes.ZonalLister,
           base_classes.InstanceGroupDynamicProperiesMixin):
  """List Google Compute Engine instance groups."""

  @staticmethod
  def Args(parser):
    base_classes.ZonalLister.Args(parser)

    managed_args_group = parser.add_mutually_exclusive_group()
    managed_args_group.add_argument(
        '--only-managed',
        action='store_true',
        help='If provided, a list of managed instance groups will be returned.')
    managed_args_group.add_argument(
        '--only-unmanaged',
        action='store_true',
        help=('If provided, a list of unmanaged instance groups '
              'will be returned.'))

  def ComputeDynamicProperties(self, args, items):
    mode = base_classes.InstanceGroupFilteringMode.all_groups
    if args.only_managed:
      mode = base_classes.InstanceGroupFilteringMode.only_managed_groups
    if args.only_unmanaged:
      mode = base_classes.InstanceGroupFilteringMode.only_unmanaged_groups
    return self.ComputeInstanceGroupManagerMembership(
        items=items, filter_mode=mode)

  @property
  def service(self):
    return self.compute.instanceGroups

  @property
  def resource_type(self):
    return 'instanceGroups'


List.detailed_help = base_classes.GetZonalListerHelp('instance groups')
