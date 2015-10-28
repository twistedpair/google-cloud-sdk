# Copyright 2015 Google Inc. All Rights Reserved.
"""Command for setting instance template of managed instance group."""
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import utils


class SetInstanceTemplate(base_classes.BaseAsyncMutator):
  """Set an instances template of managed instance group."""

  @staticmethod
  def Args(parser):
    parser.add_argument('name', help='Managed instance group name.')
    parser.add_argument(
        '--template',
        required=True,
        help=('Compute Engine instance template resource to be used.'))
    utils.AddZoneFlag(
        parser,
        resource_type='instance group manager',
        operation_type='set instance template')

  @property
  def method(self):
    return 'SetInstanceTemplate'

  @property
  def service(self):
    return self.compute.instanceGroupManagers

  @property
  def resource_type(self):
    return 'instanceGroupManagers'

  def CreateRequests(self, args):
    template_ref = self.CreateGlobalReference(
        args.template, resource_type='instanceTemplates')
    ref = self.CreateZonalReference(args.name, args.zone)
    request = (
        self.messages.ComputeInstanceGroupManagersSetInstanceTemplateRequest(
            instanceGroupManager=ref.Name(),
            instanceGroupManagersSetInstanceTemplateRequest=(
                self.messages.InstanceGroupManagersSetInstanceTemplateRequest(
                    instanceTemplate=template_ref.SelfLink(),
                )
            ),
            project=self.project,
            zone=ref.zone,)
    )
    return [request]


SetInstanceTemplate.detailed_help = {
    'brief': 'Set instance template for managed instance group.',
    'DESCRIPTION': """
        *{command}* updates the instance template for an existing managed instance group.

The new template won't apply to existing instances in the group unless they are
recreated using the recreate-instances command. But the new template does apply
to all new instances added to the managed instance group.
""",
}
