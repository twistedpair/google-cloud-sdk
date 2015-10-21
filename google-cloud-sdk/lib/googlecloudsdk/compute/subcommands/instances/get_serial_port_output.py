# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for reading the serial port output of an instance."""

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.core import log

from googlecloudsdk.shared.compute import base_classes
from googlecloudsdk.shared.compute import request_helper
from googlecloudsdk.shared.compute import utils


class GetSerialPortOutput(base_classes.BaseCommand):
  """Read output from a virtual machine instance's serial port."""

  @staticmethod
  def Args(parser):
    utils.AddZoneFlag(
        parser,
        resource_type='instance',
        operation_type='get serial port output for')

    port = parser.add_argument(
        '--port',
        help=('The number of the requested serial port. '
              'Can be 1-4, default is 1.'),
        type=arg_parsers.BoundedInt(1, 4))
    port.detailed_help = """\
        Instances can support up to four serial port outputs. By default, this
        command will return the output of the first serial port. Setting this
        flag will return the output of the requested serial port.
        """

    parser.add_argument(
        'name',
        completion_resource='compute.instances',
        help='The name of the instance.')

  @property
  def resource_type(self):
    return 'instances'

  def Run(self, args):
    instance_ref = self.CreateZonalReference(args.name, args.zone)

    request = (self.compute.instances,
               'GetSerialPortOutput',
               self.messages.ComputeInstancesGetSerialPortOutputRequest(
                   instance=instance_ref.Name(),
                   project=self.project,
                   port=args.port,
                   zone=instance_ref.zone))

    errors = []
    objects = list(request_helper.MakeRequests(
        requests=[request],
        http=self.http,
        batch_url=self.batch_url,
        errors=errors,
        custom_get_requests=None))

    if errors:
      utils.RaiseToolException(
          errors,
          error_message='Could not fetch serial port output:')
    return objects[0].contents

  def Display(self, _, response):
    log.out.write(response)


GetSerialPortOutput.detailed_help = {
    'brief': "Read output from a virtual machine instance's serial port",
    'DESCRIPTION': """\
        {command} is used to get the output from a Google Compute
        Engine virtual machine's serial port. The serial port output
        from the virtual machine will be printed to standard out. This
        information can be useful for diagnostic purposes.
        """,
}
