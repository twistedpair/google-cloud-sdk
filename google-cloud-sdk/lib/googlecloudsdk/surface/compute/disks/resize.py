# Copyright 2015 Google Inc. All Rights Reserved.
"""Command for setting size of instance group manager."""

import textwrap
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.core.console import console_io

CONTINUE_WITH_RESIZE_PROMPT = textwrap.dedent("""
    This command increases disk size. This change is not reversible.
    For more information, see:
    https://cloud.google.com/sdk/gcloud/reference/alpha/compute/disks/resize""")


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class Resize(base_classes.BaseAsyncMutator):
  """Set size of a persistent disk."""

  @property
  def service(self):
    return self.compute.disks

  @property
  def resource_type(self):
    return 'projects'

  @property
  def method(self):
    return 'Resize'

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'disk_names',
        metavar='DISK_NAME',
        nargs='+',
        completion_resource='compute.disks',
        help='The names of the disks to resize.')

    size = parser.add_argument(
        '--size',
        required=True,
        type=arg_parsers.BinarySize(lower_bound='1GB'),
        help='Indicates the new size of the disks.')
    size.detailed_help = """\
        Indicates the new size of the disks. The value must be a whole
        number followed by a size unit of ``KB'' for kilobyte, ``MB''
        for megabyte, ``GB'' for gigabyte, or ``TB'' for terabyte. For
        example, ``10GB'' will produce 10 gigabyte disks.  Disk size
        must be a multiple of 10 GB.
        """

    utils.AddZoneFlag(
        parser,
        resource_type='disks',
        operation_type='be resized')

  def CreateRequests(self, args):
    """Returns a request for resizing a disk."""

    size_gb = utils.BytesToGb(args.size)

    disk_refs = self.CreateZonalReferences(
        args.disk_names, args.zone, resource_type='disks')

    console_io.PromptContinue(
        message=CONTINUE_WITH_RESIZE_PROMPT,
        cancel_on_no=True)

    requests = []

    for disk_ref in disk_refs:
      request = self.messages.ComputeDisksResizeRequest(
          disk=disk_ref.Name(),
          project=self.project,
          zone=disk_ref.zone,
          disksResizeRequest=self.messages.DisksResizeRequest(sizeGb=size_gb))
      requests.append(request)

    return requests

Resize.detailed_help = {
    'brief': 'Resize a disk or disks',
    'DESCRIPTION': """\
        *{command}* resizes a Google Compute Engine disk(s).
        Only increasing in disk size is supported. Disks can be resized
        regardless or whether they are attached or not.

        For example, running:

        $ *{command}* example-disk-1,example-disk-2 --size=6TB

        will resize the disk called example-disk-1 to new size 6TB,
        this assumes that original size of example-disk-1 is 6TB or less.
    """}
