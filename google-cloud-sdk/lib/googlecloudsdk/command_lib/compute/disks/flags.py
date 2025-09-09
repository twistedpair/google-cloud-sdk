# -*- coding: utf-8 -*- #
# Copyright 2016 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Flags and helpers for the compute disks commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import actions
from googlecloudsdk.command_lib.compute import completers as compute_completers
from googlecloudsdk.command_lib.compute import flags as compute_flags
from googlecloudsdk.command_lib.util import completers
from googlecloudsdk.core import properties

_DETAILED_SOURCE_SNAPSHOT_HELP = """\
      Source snapshot used to create the disks. It is safe to
      delete a snapshot after a disk has been created from the
      snapshot. In such cases, the disks will no longer reference
      the deleted snapshot. To get a list of snapshots in your
      current project, run `gcloud compute snapshots list`. A
      snapshot from an existing disk can be created using the
      `gcloud compute disks snapshot` command. This flag is mutually
      exclusive with *--image*.

      When using this option, the size of the disks must be at least
      as large as the snapshot size. Use *--size* to adjust the
      size of the disks.
"""

_DETAILED_SOURCE_INSTANT_SNAPSHOT_HELP = """\
      Name of the source instant snapshot used to create the disks.
"""

_DETAILED_SOURCE_INSTANT_SNAPSHOT_PROJECT_HELP = """\
      The project containing the instant snapshot used to create the disks.
"""

_SOURCE_DISK_DETAILED_HELP = """\
      Source disk used to create the disk(s). It is safe to
      delete a source disk after a disk has been created from the
      source disk. To get a list of disks in your current project,
      run `gcloud compute disks list`. This flag is mutually
      exclusive with *--image* and *--source-snapshot*.

      When using this option, the size of the disks must be at least
      as large as the source disk size. Use *--size* to adjust the
      size of the disks.

      The source disk must be in the same zone/region as the disk to be created.
"""

_SOURCE_DISK_ZONE_EXPLANATION = """\
      Zone of the source disk. This argument is not required if the target disk
      is in the same zone as the source disk.
"""

_SOURCE_DISK_REGION_EXPLANATION = """\
      Region of the source disk. This argument is not required if the target
      disk is in the same region as the source disk.
"""

_ASYNC_PRIMARY_DISK_HELP = """\
      Primary disk for asynchronous replication. This flag is required when
      creating a secondary disk.
"""

_ASYNC_PRIMARY_DISK_ZONE_EXPLANATION = """\
      Zone of the primary disk for asynchronous replication. The primary and
      secondary disks must not be in the same region.
"""

_ASYNC_PRIMARY_DISK_REGION_EXPLANATION = """\
      Region of the primary disk for asynchronous replication. The primary and
      secondary disks must not be in the same region.
"""

_ASYNC_SECONDARY_DISK_HELP = """\
      Secondary disk for asynchronous replication. This flag is required when
      starting replication.
"""

_ASYNC_SECONDARY_DISK_ZONE_EXPLANATION = """\
      Zone of the secondary disk for asynchronous replication.
"""

_ASYNC_SECONDARY_DISK_REGION_EXPLANATION = """\
      Region of the secondary disk for asynchronous replication.
"""

_ASYNC_SECONDARY_DISK_PROJECT_EXPLANATION = """\
      Project of the secondary disk for asynchronous replication.
"""

_ASYNC_PRIMARY_DISK_PROJECT_EXPLANATION = """\
      Project of the primary disk for asynchronous replication.
"""

DEFAULT_LIST_FORMAT = """\
    table(
      name,
      zone.basename(),
      sizeGb,
      type.basename(),
      status
    )"""


MULTISCOPE_LIST_FORMAT = """
    table(
      name,
      location(),
      location_scope(),
      sizeGb,
      type.basename(),
      status
      )"""


class SnapshotsCompleter(compute_completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(SnapshotsCompleter, self).__init__(
        collection='compute.snapshots',
        list_command='compute snapshots list --uri',
        **kwargs)


class SnapshotGroupsCompleter(compute_completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(SnapshotGroupsCompleter, self).__init__(
        collection='compute.snapshotGroups',
        list_command='alpha compute snapshot-groups list --uri',
        api_version='alpha',
        **kwargs)


class SnapshotsCompleterAlpha(completers.MultiResourceCompleter):

  def __init__(self, **kwargs):
    super(SnapshotsCompleterAlpha, self).__init__(
        completers=[RegionSnapshotsCompleter, GlobalSnapshotsCompleter],
        **kwargs
    )


class GlobalSnapshotsCompleter(compute_completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(GlobalSnapshotsCompleter, self).__init__(
        collection='compute.snapshots',
        list_command='compute snapshots list --uri',
        api_version='alpha',
        **kwargs
    )


class RegionSnapshotsCompleter(compute_completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(RegionSnapshotsCompleter, self).__init__(
        collection='compute.regionSnapshots',
        list_command='compute regionSnapshots list --uri',
        api_version='alpha',
        **kwargs
    )


def MakeDiskArgZonal(plural):
  return compute_flags.ResourceArgument(
      resource_name='disk',
      completer=compute_completers.DisksCompleter,
      plural=plural,
      name='DISK_NAME',
      zonal_collection='compute.disks',
      zone_explanation=compute_flags.ZONE_PROPERTY_EXPLANATION)


def MakeDiskArg(plural):
  return compute_flags.ResourceArgument(
      resource_name='disk',
      completer=compute_completers.DisksCompleter,
      plural=plural,
      name='DISK_NAME',
      zonal_collection='compute.disks',
      regional_collection='compute.regionDisks',
      zone_explanation=compute_flags.ZONE_PROPERTY_EXPLANATION,
      region_explanation=compute_flags.REGION_PROPERTY_EXPLANATION)


def AddMultiWriterFlag(parser):
  return parser.add_argument(
      '--multi-writer',
      action='store_true',
      help="""
      Create the disk in multi-writer mode so that it can be attached
      with read-write access to two VMs. The multi-writer feature requires
      specialized filesystems, among other restrictions. For more information,
      see
      https://cloud.google.com/compute/docs/disks/sharing-disks-between-vms.
      """)


def AddEnableConfidentialComputeFlag(parser):
  return parser.add_argument(
      '--confidential-compute',
      action='store_true',
      help="""
      Creates the disk with confidential compute mode enabled. Encryption with a Cloud KMS key is required to enable this option.
      """,
  )


def AddStopGroupAsyncReplicationArgs(parser):
  """Adds stop group async replication specific arguments to parser."""
  parser.add_argument(
      'DISK_CONSISTENCY_GROUP_POLICY',
      help='URL of the disk consistency group resource policy. The resource'
           'policy is always in the region of the primary disks.'
  )

  help_text = '{0} of the consistency group\'s primary or secondary disks. {1}'
  scope_parser = parser.add_mutually_exclusive_group()
  scope_parser.add_argument(
      '--zone',
      completer=compute_completers.ZonesCompleter,
      action=actions.StoreProperty(properties.VALUES.compute.zone),
      help=help_text.format('Zone', compute_flags.ZONE_PROPERTY_EXPLANATION))
  scope_parser.add_argument(
      '--region',
      completer=compute_completers.RegionsCompleter,
      action=actions.StoreProperty(properties.VALUES.compute.region),
      help=help_text.format(
          'Region',
          compute_flags.REGION_PROPERTY_EXPLANATION))


def AddBulkCreateArgs(parser):
  """Adds bulk create specific arguments to parser."""
  parser.add_argument(
      '--source-consistency-group-policy',
      help='''
      URL of the source consistency group resource policy. The resource policy
      is always the same region as the source disks.
      ''',
      # This argument is required because consistent cloning is only supported
      # feature under the BulkCreate now. May become optional in the future.
      required=True)

  help_text = """Target {0} of the created disks, which currently must be the same as the source {0}. {1}"""
  scope_parser = parser.add_mutually_exclusive_group(required=True)
  scope_parser.add_argument(
      '--zone',
      completer=compute_completers.ZonesCompleter,
      action=actions.StoreProperty(properties.VALUES.compute.zone),
      help=help_text.format('zone', compute_flags.ZONE_PROPERTY_EXPLANATION))
  scope_parser.add_argument(
      '--region',
      completer=compute_completers.RegionsCompleter,
      action=actions.StoreProperty(properties.VALUES.compute.region),
      help=help_text.format('region',
                            compute_flags.REGION_PROPERTY_EXPLANATION))


def AddBulkCreateArgsAlpha(parser):
  """Adds bulk create specific arguments to parser."""
  parser.add_argument(
      '--source-consistency-group-policy',
      help='''
      URL of the source consistency group resource policy. The resource policy
      is always the same region as the source disks.
      ''',
      # This argument is optional because we now support bulk insert from
      # multiple source types.
      required=False)

  help_text = """Target {0} of the created disks, which currently must be the same as the source {0}. {1}"""
  scope_parser = parser.add_mutually_exclusive_group(required=True)
  scope_parser.add_argument(
      '--zone',
      completer=compute_completers.ZonesCompleter,
      action=actions.StoreProperty(properties.VALUES.compute.zone),
      help=help_text.format('zone', compute_flags.ZONE_PROPERTY_EXPLANATION))
  scope_parser.add_argument(
      '--region',
      completer=compute_completers.RegionsCompleter,
      action=actions.StoreProperty(properties.VALUES.compute.region),
      help=help_text.format('region',
                            compute_flags.REGION_PROPERTY_EXPLANATION))


def AddProvisionedIopsFlag(parser, arg_parsers):
  return parser.add_argument(
      '--provisioned-iops',
      type=arg_parsers.BoundedInt(),
      help=(
          'Provisioned IOPS of disk to create. Only for use with disks of type '
          'pd-extreme and hyperdisk-extreme.'
      ),
  )


def AddProvisionedThroughputFlag(parser, arg_parsers):
  return parser.add_argument(
      '--provisioned-throughput',
      type=arg_parsers.BoundedInt(),
      help=(
          'Provisioned throughput of disk to create. The throughput unit is  '
          'MB per sec.  Only for use with disks of type hyperdisk-throughput.'))


def AddArchitectureFlag(parser, messages):
  architecture_enum_type = messages.Disk.ArchitectureValueValuesEnum
  excluded_enums = [architecture_enum_type.ARCHITECTURE_UNSPECIFIED.name]
  architecture_choices = sorted(
      [e for e in architecture_enum_type.names() if e not in excluded_enums])
  return parser.add_argument(
      '--architecture',
      choices=architecture_choices,
      help=(
          'Specifies the architecture or processor type that this disk can '
          'support. For available processor types on Compute Engine, '
          'see https://cloud.google.com/compute/docs/cpu-platforms.'
      ),
  )


def AddAccessModeFlag(parser, messages):
  if hasattr(messages.Disk, 'AccessModeValueValuesEnum'):
    access_mode_enum_type = messages.Disk.AccessModeValueValuesEnum
    return parser.add_argument(
        '--access-mode',
        choices=access_mode_enum_type.names(),
        help=(
            'Specifies how VMs attached to the disk can access the data on the'
            ' disk. To grant read-only access to multiple VMs attached to the'
            ' disk, set access-mode to READ_ONLY_MANY.'
            ' To grant read-write access'
            ' to only one VM attached to the disk, use READ_WRITE_SINGLE.'
            ' READ_WRITE_SINGLE is used if omitted.'
        ),
    )


def AddLocationHintArg(parser):
  parser.add_argument(
      '--location-hint',
      hidden=True,
      help="""\
      Used by internal tools to control sub-zone location of the disk.
      """)


def MakeSecondaryDiskArg(required=False):
  return compute_flags.ResourceArgument(
      resource_name='async secondary disk',
      name='--secondary-disk',
      completer=compute_completers.DisksCompleter,
      zonal_collection='compute.disks',
      regional_collection='compute.regionDisks',
      short_help='Secondary disk for asynchronous replication.',
      detailed_help=_ASYNC_SECONDARY_DISK_HELP,
      plural=False,
      required=required,
      scope_flags_usage=compute_flags.ScopeFlagsUsage
      .GENERATE_DEDICATED_SCOPE_FLAGS,
      zone_help_text=_ASYNC_SECONDARY_DISK_ZONE_EXPLANATION,
      region_help_text=_ASYNC_SECONDARY_DISK_REGION_EXPLANATION)


def AddSecondaryDiskProject(parser, category=None):
  parser.add_argument(
      '--secondary-disk-project',
      category=category,
      help=_ASYNC_SECONDARY_DISK_PROJECT_EXPLANATION,
  )


def AddPrimaryDiskProject(parser, category=None):
  parser.add_argument(
      '--primary-disk-project',
      category=category,
      help=_ASYNC_PRIMARY_DISK_PROJECT_EXPLANATION,
  )


def AddKeepOldDiskArgs(parser):
  """Adds keep old disk argument group to parser."""
  group = parser.add_group()
  group.add_argument(
      '--keep-old-disk',
      action='store_true',
      help=(
          'If true, the old disk will be kept after the conversion. '
          'The old disk will be renamed to the original disk name with a '
          'suffix.'
      ),
  )
  group.add_argument(
      '--target-disk-name',
      help=(
          'Specifies the name of the new disk, '
          'it can only be used with --keep-old-disk.'
          ' For details on the naming convention for this '
          'resource, refer to: '
          'https://cloud.google.com/compute/docs/'
          'naming-resources'
      ),
  )


def AddGuestOsFeatureArgs(parser, messages):
  group = parser.add_group()
  guest_os_feature_choices = [
      messages.GuestOsFeature.TypeValueValuesEnum.GVNIC.name
  ]
  group.add_argument(
      '--add-guest-os-features',
      choices=guest_os_feature_choices,
      help=(
          'Specifies guest OS features to add to the disk. Refer to'
          ' https://cloud.google.com/compute/docs/images/create-custom#guest-os-features'
          ' for a list of available options.'
      ),
  )


def AddSourceInstantSnapshotProject(parser, category=None):
  parser.add_argument(
      '--source-instant-snapshot-project',
      category=category,
      help=_DETAILED_SOURCE_INSTANT_SNAPSHOT_PROJECT_HELP,
  )

SOURCE_SNAPSHOT_ARG = compute_flags.ResourceArgument(
    resource_name='snapshot',
    completer=SnapshotsCompleter,
    name='--source-snapshot',
    plural=False,
    required=False,
    global_collection='compute.snapshots',
    short_help='Source snapshot used to create the disks.',
    detailed_help=_DETAILED_SOURCE_SNAPSHOT_HELP,
)

SOURCE_SNAPSHOT_ARG_ALPHA = compute_flags.ResourceArgument(
    resource_name='snapshot',
    completer=SnapshotsCompleterAlpha,
    name='--source-snapshot',
    plural=False,
    required=False,
    global_collection='compute.snapshots',
    regional_collection='compute.regionSnapshots',
    short_help='Source snapshot used to create the disks.',
    detailed_help=_DETAILED_SOURCE_SNAPSHOT_HELP,
)

SOURCE_INSTANT_SNAPSHOT_ARG = compute_flags.ResourceArgument(
    resource_name='source instant snapshot',
    completer=compute_completers.InstantSnapshotsCompleter,
    name='--source-instant-snapshot',
    zonal_collection='compute.instantSnapshots',
    regional_collection='compute.regionInstantSnapshots',
    plural=False,
    required=False,
    short_help='Name of the source instant snapshot used to create the disks.',
    detailed_help=_DETAILED_SOURCE_INSTANT_SNAPSHOT_HELP,
    scope_flags_usage=compute_flags.ScopeFlagsUsage.USE_EXISTING_SCOPE_FLAGS)

SOURCE_INSTANT_SNAPSHOT_GROUP_ARG = compute_flags.ResourceArgument(
    resource_name='source instant snapshot group',
    name='--source-instant-snapshot-group',
    completer=compute_completers.InstantSnapshotGroupsCompleter,
    short_help='Source instant snapshot group used to create the disks.',
    zonal_collection='compute.instantSnapshotGroups',
    regional_collection='compute.regionInstantSnapshotGroups',
    required=False,
)

SOURCE_SNAPSHOT_GROUP_ARG = compute_flags.ResourceArgument(
    resource_name='source snapshot group',
    name='--source-snapshot-group',
    completer=SnapshotGroupsCompleter,
    short_help='Source snapshot group used to create the disks.',
    global_collection='compute.snapshotGroups',
    required=False,
)

SOURCE_DISK_ARG = compute_flags.ResourceArgument(
    resource_name='source disk',
    name='--source-disk',
    completer=compute_completers.DisksCompleter,
    short_help='Source disk used to create the disks. Source disk must be in'
    ' the same zone/region as the disk to be created.',
    detailed_help=_SOURCE_DISK_DETAILED_HELP,
    zonal_collection='compute.disks',
    regional_collection='compute.regionDisks',
    required=False,
    zone_help_text=_SOURCE_DISK_ZONE_EXPLANATION,
    region_help_text=_SOURCE_DISK_REGION_EXPLANATION)

ASYNC_PRIMARY_DISK_ARG = compute_flags.ResourceArgument(
    resource_name='async primary disk',
    name='--primary-disk',
    completer=compute_completers.DisksCompleter,
    zonal_collection='compute.disks',
    regional_collection='compute.regionDisks',
    short_help='Primary disk for asynchronous replication. This option creates'
    ' a secondary disk for a given primary disk.',
    detailed_help=_ASYNC_PRIMARY_DISK_HELP,
    plural=False,
    required=False,
    scope_flags_usage=compute_flags.ScopeFlagsUsage
    .GENERATE_DEDICATED_SCOPE_FLAGS,
    zone_help_text=_ASYNC_PRIMARY_DISK_ZONE_EXPLANATION,
    region_help_text=_ASYNC_PRIMARY_DISK_REGION_EXPLANATION)

STORAGE_POOL_ARG = compute_flags.ResourceArgument(
    resource_name='storage pool',
    name='--storage-pool',
    short_help=('Specifies the URI of the storage pool in which the disk is '
                'created.'),
    zonal_collection='compute.storagePools',
    plural=False,
    required=False,
    scope_flags_usage=compute_flags.ScopeFlagsUsage.USE_EXISTING_SCOPE_FLAGS)


def AddSourceMachineImageNameArg(parser):
  # TODO: b/421424530 - switch to compute_flags.ResourceArgument when
  # disks.insert goes GA. compute_flags.ResourceArgument does not support
  # the hidden flag.
  parser.add_argument(
      '--source-machine-image',
      help="""\
        Specifies the URI of the source machine image contiaining the disk to
        restore. Requires *--source-machine-image-disk-device-name* with the
        disk to restores device name.
      """,
      hidden=True,
  )


def AddSourceMachineImageDiskDeviceNameArg(parser):
  parser.add_argument(
      '--source-machine-image-disk-device-name',
      help="""\
        Specifies the name of the disk to be restored from the source machine
        image. Requires *--source-machine-image* with the URI of the source
        machine image.
      """,
      hidden=True,
  )
