# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for describing instances."""
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import resource_specs


class Describe(base_classes.ZonalDescriber):
  """Describe a virtual machine instance."""

  @staticmethod
  def Args(parser):
    base_classes.ZonalDescriber.Args(parser, 'compute.instances')
    base_classes.AddFieldsFlag(parser, 'instances')

  @property
  def service(self):
    return self.compute.instances

  @property
  def resource_type(self):
    return 'instances'

  def ComputeDynamicProperties(self, args, items):
    # This is an overridden function that modifies the output of the custom
    # machine type in instances describe.
    # (TODO:spencertung) Possibly not the best way to deal with modifying
    # the items output (b/25603716)
    items_list = list(items)
    machine_type = resource_specs.FormatDescribeMachineTypeName(
        items_list,
        args.command_path)
    if machine_type:
      items_list[0]['machineType'] = machine_type
    if not items_list:
      yield items_list
    else:
      yield items_list[0]

Describe.detailed_help = {
    'brief': 'Describe a virtual machine instance',
    'DESCRIPTION': """\
        *{command}* displays all data associated with a Google Compute
        Engine virtual machine instance.
        """,
}
