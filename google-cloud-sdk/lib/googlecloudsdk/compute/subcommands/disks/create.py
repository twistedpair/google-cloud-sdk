# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for creating disks."""
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.shared.compute import base_classes
from googlecloudsdk.shared.compute import constants
from googlecloudsdk.shared.compute import csek_utils
from googlecloudsdk.shared.compute import image_utils
from googlecloudsdk.shared.compute import utils
from googlecloudsdk.shared.compute import zone_utils


DETAILED_HELP = {
    'brief': 'Create Google Compute Engine persistent disks',
    'DESCRIPTION': """\
        *{command}* creates one or more Google Compute Engine
        persistent disks. When creating virtual machine instances,
        disks can be attached to the instances through the
        `gcloud compute instances create` command. Disks can also be
        attached to instances that are already running using
        `gcloud compute instances attach-disk`.

        Disks are zonal resources, so they reside in a particular zone
        for their entire lifetime. The contents of a disk can be moved
        to a different zone by snapshotting the disk (using
        `gcloud compute disks snapshot`) and creating a new disk using
        `--source-snapshot` in the desired zone. The contents of a
        disk can also be moved across project or zone by creating an
        image (using 'gcloud compute images create') and creating a
        new disk using `--image` in the desired project and/or
        zone.

        When creating disks, be sure to include the `--zone` option:

          $ {command} my-disk-1 my-disk-2 --zone us-east1-a
        """,
}


def _CommonArgs(parser):
  """Add arguments used for parsing in all command tracks."""
  parser.add_argument(
      '--description',
      help=(
          'An optional, textual description for the disks being created.'))

  size = parser.add_argument(
      '--size',
      type=arg_parsers.BinarySize(lower_bound='1GB'),
      help='Indicates the size of the disks.')
  size.detailed_help = """\
      Indicates the size of the disks. The value must be a whole
      number followed by a size unit of ``KB'' for kilobyte, ``MB''
      for megabyte, ``GB'' for gigabyte, or ``TB'' for terabyte. For
      example, ``10GB'' will produce 10 gigabyte disks.  Disk size
      must be a multiple of 10 GB.
      """

  parser.add_argument(
      'names',
      metavar='NAME',
      nargs='+',
      help='The names of the disks to create.')

  source_group = parser.add_mutually_exclusive_group()

  def AddImageHelp():
    """Returns detailed help for `--image` argument."""
    template = """\
        An image to apply to the disks being created. When using
        this option, the size of the disks must be at least as large as
        the image size. Use ``--size'' to adjust the size of the disks.

        {alias_table}

        This flag is mutually exclusive with ``--source-snapshot''.
        """
    indent = template.find(template.lstrip()[0])
    return template.format(
        alias_table=image_utils.GetImageAliasTable(indent=indent))

  image = source_group.add_argument(
      '--image',
      help='An image to apply to the disks being created.')
  image.detailed_help = AddImageHelp

  image_utils.AddImageProjectFlag(parser)

  source_snapshot = source_group.add_argument(
      '--source-snapshot',
      help='A source snapshot used to create the disks.')
  source_snapshot.detailed_help = """\
      A source snapshot used to create the disks. It is safe to
      delete a snapshot after a disk has been created from the
      snapshot. In such cases, the disks will no longer reference
      the deleted snapshot. To get a list of snapshots in your
      current project, run `gcloud compute snapshots list`. A
      snapshot from an existing disk can be created using the
      'gcloud compute disks snapshot' command. This flag is mutually
      exclusive with ``--image''.

      When using this option, the size of the disks must be at least
      as large as the snapshot size. Use ``--size'' to adjust the
      size of the disks.
      """

  disk_type = parser.add_argument(
      '--type',
      help='Specifies the type of disk to create.')
  disk_type.detailed_help = """\
      Specifies the type of disk to create. To get a
      list of available disk types, run 'gcloud compute
      disk-types list'. The default disk type is pd-standard.
      """

  utils.AddZoneFlag(
      parser,
      resource_type='disks',
      operation_type='create')


@base.ReleaseTracks(base.ReleaseTrack.GA)
class CreateGA(base_classes.BaseAsyncCreator, image_utils.ImageExpander,
               zone_utils.ZoneResourceFetcher):
  """Create Google Compute Engine persistent disks."""

  @staticmethod
  def Args(parser):
    _CommonArgs(parser)

  @property
  def service(self):
    return self.compute.disks

  @property
  def method(self):
    return 'Insert'

  @property
  def resource_type(self):
    return 'disks'

  def CreateRequests(self, args):
    """Returns a list of requests necessary for adding disks."""
    size_gb = utils.BytesToGb(args.size)

    if not size_gb and not args.source_snapshot and not args.image:
      if args.type and 'pd-ssd' in args.type:
        size_gb = constants.DEFAULT_SSD_DISK_SIZE_GB
      else:
        size_gb = constants.DEFAULT_STANDARD_DISK_SIZE_GB

    utils.WarnIfDiskSizeIsTooSmall(size_gb, args.type)

    requests = []

    disk_refs = self.CreateZonalReferences(args.names, args.zone)

    # Check if the zone is deprecated or has maintenance coming.
    self.WarnForZonalCreation(disk_refs)

    if args.image:
      source_image_uri, _ = self.ExpandImageFlag(
          args, return_image_resource=False)
    else:
      source_image_uri = None

    if args.source_snapshot:
      snapshot_ref = self.CreateGlobalReference(
          args.source_snapshot, resource_type='snapshots')
      snapshot_uri = snapshot_ref.SelfLink()
    else:
      snapshot_uri = None

    if hasattr(args, 'csek_key_file'):
      csek_keys = csek_utils.CsekKeyStore.FromArgs(args)
    else:
      csek_keys = None

    image_key_message_or_none, snapshot_key_message_or_none = (
        csek_utils.MaybeLookupKeyMessagesByUri(
            csek_keys, self.resources, [source_image_uri, snapshot_uri],
            self.compute))

    for disk_ref in disk_refs:
      if args.type:
        type_ref = self.CreateZonalReference(
            args.type, disk_ref.zone,
            resource_type='diskTypes')
        type_uri = type_ref.SelfLink()
      else:
        type_uri = None

      if csek_keys:
        disk_key_or_none = csek_keys.LookupKey(
            disk_ref, args.require_csek_key_create)
        disk_key_message_or_none = csek_utils.MaybeToMessage(
            disk_key_or_none, self.compute)
        kwargs = {'diskEncryptionKey': disk_key_message_or_none,
                  'sourceImageEncryptionKey': image_key_message_or_none,
                  'sourceSnapshotEncryptionKey': snapshot_key_message_or_none}
      else:
        kwargs = {}

      request = self.messages.ComputeDisksInsertRequest(
          disk=self.messages.Disk(
              name=disk_ref.Name(),
              description=args.description,
              sizeGb=size_gb,
              sourceSnapshot=snapshot_uri,
              type=type_uri,
              **kwargs),
          project=self.project,
          sourceImage=source_image_uri,
          zone=disk_ref.zone)
      requests.append(request)

    return requests


@base.ReleaseTracks(base.ReleaseTrack.ALPHA, base.ReleaseTrack.BETA)
class CreateAlphaBeta(CreateGA):
  """Create Google Compute Engine persistent disks."""

  @staticmethod
  def Args(parser):
    _CommonArgs(parser)
    csek_utils.AddCsekKeyArgs(parser)


CreateGA.detailed_help = DETAILED_HELP
CreateAlphaBeta.detailed_help = DETAILED_HELP
