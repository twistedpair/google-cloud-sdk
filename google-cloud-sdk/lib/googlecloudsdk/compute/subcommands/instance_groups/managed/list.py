# Copyright 2015 Google Inc. All Rights Reserved.
"""Command for listing managed instance groups."""
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import managed_instance_groups_utils


# TODO(user): This acts like
# instance-groups list --only-managed
# so they should share code.
class List(base_classes.ZonalLister,
           base_classes.InstanceGroupManagerDynamicProperiesMixin):
  """List Google Compute Engine managed instance groups."""

  @property
  def service(self):
    return self.compute.instanceGroupManagers

  @property
  def resource_type(self):
    return 'instanceGroupManagers'

  def ComputeDynamicProperties(self, args, items):
    """Add Autoscaler information if Autoscaler is defined for the item."""
    # Items are expected to be IGMs.
    for mig in managed_instance_groups_utils.AddAutoscalersToMigs(
        migs_iterator=self.ComputeInstanceGroupSize(items=items),
        project=self.project,
        compute=self.compute,
        http=self.http,
        batch_url=self.batch_url,
        fail_when_api_not_supported=False):
      if 'autoscaler' in mig and mig['autoscaler'] is not None:
        mig['autoscaled'] = 'yes'
      else:
        mig['autoscaled'] = 'no'
      yield mig


List.detailed_help = base_classes.GetZonalListerHelp('managed instance groups')
