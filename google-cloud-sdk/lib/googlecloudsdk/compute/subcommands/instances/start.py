# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for starting an instance."""
from googlecloudsdk.shared.compute import base_classes
from googlecloudsdk.shared.compute import utils


class Start(base_classes.NoOutputAsyncMutator):
  """Start a stopped virtual machine instance.

  *{command}* is used to start a stopped Google Compute Engine virtual machine.
  Only a stopped virtual machine can be started.
  """

  @staticmethod
  def Args(parser):
    utils.AddZoneFlag(
        parser,
        resource_type='instance',
        operation_type='start')

    parser.add_argument(
        'name',
        nargs='+',
        completion_resource='compute.instances',
        help='The names of the instances to start.')

  @property
  def service(self):
    return self.compute.instances

  @property
  def method(self):
    return 'Start'

  @property
  def resource_type(self):
    return 'instances'

  def CreateRequests(self, args):
    request_list = []
    for name in args.name:
      instance_ref = self.CreateZonalReference(name, args.zone)

      request = self.messages.ComputeInstancesStartRequest(
          instance=instance_ref.Name(),
          project=self.project,
          zone=instance_ref.zone)

      request_list.append(request)
    return request_list

  def Display(self, _, resources):
    # There is no need to display anything when starting an
    # instance. Instead, we consume the generator returned from Run()
    # to invoke the logic that waits for the start to complete.
    list(resources)
