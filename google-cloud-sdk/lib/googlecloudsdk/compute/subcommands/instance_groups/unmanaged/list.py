# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for listing unmanaged instance groups."""
from googlecloudsdk.api_lib.compute import base_classes


class List(base_classes.ZonalLister,
           base_classes.InstanceGroupDynamicProperiesMixin):
  """List Google Compute Engine unmanaged instance groups."""

  def ComputeDynamicProperties(self, args, items):
    mode = base_classes.InstanceGroupFilteringMode.only_unmanaged_groups
    return self.ComputeInstanceGroupManagerMembership(
        items=items, filter_mode=mode)

  @property
  def service(self):
    return self.compute.instanceGroups

  @property
  def resource_type(self):
    return 'instanceGroups'


List.detailed_help = base_classes.GetZonalListerHelp('unmanaged '
                                                     'instance groups')
