# Copyright 2015 Google Inc. All Rights Reserved.
"""Command for describing managed instance groups."""
from googlecloudsdk.shared.compute import base_classes
from googlecloudsdk.shared.compute import managed_instance_groups_utils


class Describe(base_classes.ZonalDescriber):
  """Describe a managed instance group."""

  @staticmethod
  def Args(parser):
    base_classes.ZonalDescriber.Args(parser)
    base_classes.AddFieldsFlag(parser, 'instanceGroupManagers')

  @property
  def service(self):
    return self.compute.instanceGroupManagers

  @property
  def resource_type(self):
    return 'instanceGroupManagers'

  def ComputeDynamicProperties(self, args, items):
    """Add Autoscaler information if Autoscaler is defined for the item."""
    # Items are expected to be IGMs.
    return managed_instance_groups_utils.AddAutoscalersToMigs(
        migs_iterator=items,
        project=self.project,
        compute=self.compute,
        http=self.http,
        batch_url=self.batch_url,
        fail_when_api_not_supported=False)


Describe.detailed_help = {
    'brief': 'Describe a managed instance group',
    'DESCRIPTION': """\
        *{command}* displays all data associated with a Google Compute Engine
managed instance group.
""",
}
