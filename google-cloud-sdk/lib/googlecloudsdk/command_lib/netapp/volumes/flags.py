# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Flags and helpers for the Cloud NetApp Files Volumes commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import argparse
import textwrap
from typing import Any

from googlecloudsdk.api_lib.netapp import util as netapp_api_util
from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base as calliope_base
from googlecloudsdk.command_lib.netapp import flags
from googlecloudsdk.command_lib.netapp import util as netapp_util
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.command_lib.util.args import labels_util
from googlecloudsdk.command_lib.util.concepts import concept_parsers


VOLUMES_LIST_FORMAT = """\
    table(
        name.basename():label=VOLUME_NAME:sort=1,
        name.segment(3):label=LOCATION,
        storagePool,
        capacityGib:label=CAPACITY_GB,
        serviceLevel,
        shareName,
        state
    )"""

## Helper functions to add args / flags for Volumes gcloud commands ##


def AddVolumeAssociatedStoragePoolArg(parser, required=True):
  concept_parsers.ConceptParser.ForResource(
      '--storage-pool',
      flags.GetStoragePoolResourceSpec(),
      'The Storage Pool to associate with Volume.',
      required=required,
      flag_name_overrides={'location': ''},
  ).AddToParser(parser)


def AddVolumeNetworkArg(parser, required=True):
  """Adds a --network arg to the given parser.

  Args:
    parser: argparse parser.
    required: bool whether arg is required or not
  """

  network_arg_spec = {
      'name': str,
      'psa-range': str,
  }

  network_help = textwrap.dedent("""\
        Network configuration for a Cloud NetApp Files Volume. Specifying
        `psa-range` is optional.
        *name*::: The name of the Google Compute Engine
        [VPC network](/compute/docs/networks-and-firewalls#networks) to which
        the volume is connected.
        *psa-range*::: This field is not implemented. The values provided in
        this field are ignored.
  """)

  parser.add_argument(
      '--network',
      type=arg_parsers.ArgDict(spec=network_arg_spec, required_keys=['name']),
      required=required,
      help=network_help,
  )


def GetVolumeProtocolEnumFromArg(choice, messages):
  """Returns the Choice Enum for Protocols.

  Args:
    choice: The choice for protocol input as string
    messages: The messages module.

  Returns:
    the protocol enum
  """
  return arg_utils.ChoiceToEnum(
      choice=choice, enum_type=messages.Volume.ProtocolsValueListEntryValuesEnum
  )


def AddVolumeProtocolsArg(parser, required=True):
  """Adds the Protocols arg to the arg parser."""
  parser.add_argument(
      '--protocols',
      type=arg_parsers.ArgList(min_length=1, element_type=str),
      required=required,
      metavar='PROTOCOL',
      help="""Type of File System protocols for the Cloud NetApp Files Volume. \
Valid component values are:
            `NFSV3`, `NFSV4`, `SMB`.""",
  )


def AddVolumeShareNameArg(parser, required=False):
  """Adds the Share name arg to the arg parser."""
  parser.add_argument(
      '--share-name',
      type=str,
      required=required,
      help="""Share name of the Mount path clients will use.""",
  )


def AddVolumeExportPolicyArg(parser: argparse.ArgumentParser, messages: Any):
  """Adds the Export Policy (--export-policy) arg to the given parser.

  Args:
    parser: argparse parser.
    messages: The messages module.
  """
  export_policy_arg_spec = {
      'allowed-clients': str,
      'has-root-access': str,
      'access-type': str,
      'kerberos-5-read-only': arg_parsers.ArgBoolean(
          truthy_strings=netapp_util.truthy, falsey_strings=netapp_util.falsey
      ),
      'kerberos-5-read-write': arg_parsers.ArgBoolean(
          truthy_strings=netapp_util.truthy, falsey_strings=netapp_util.falsey
      ),
      'kerberos-5i-read-only': arg_parsers.ArgBoolean(
          truthy_strings=netapp_util.truthy, falsey_strings=netapp_util.falsey
      ),
      'kerberos-5i-read-write': arg_parsers.ArgBoolean(
          truthy_strings=netapp_util.truthy, falsey_strings=netapp_util.falsey
      ),
      'kerberos-5p-read-write': arg_parsers.ArgBoolean(
          truthy_strings=netapp_util.truthy, falsey_strings=netapp_util.falsey
      ),
      'kerberos-5p-read-only': arg_parsers.ArgBoolean(
          truthy_strings=netapp_util.truthy, falsey_strings=netapp_util.falsey
      ),
      'nfsv3': arg_parsers.ArgBoolean(
          truthy_strings=netapp_util.truthy, falsey_strings=netapp_util.falsey
      ),
      'nfsv4': arg_parsers.ArgBoolean(
          truthy_strings=netapp_util.truthy, falsey_strings=netapp_util.falsey
      ),
      'squash-mode': messages.SimpleExportPolicyRule.SquashModeValueValuesEnum,
      'anon-uid': int,
  }
  export_policy_help = textwrap.dedent("""\
        Export Policy of a Cloud NetApp Files Volume.
        This will be a field similar to network
        in which export policy fields can be specified as such:
        `--export-policy=allowed-clients=ALLOWED_CLIENTS_IP_ADDRESSES,
        has-root-access=HAS_ROOT_ACCESS_BOOL,access=ACCESS_TYPE,nfsv3=NFSV3,
        nfsv4=NFSV4,kerberos-5-read-only=KERBEROS_5_READ_ONLY,
        kerberos-5-read-write=KERBEROS_5_READ_WRITE,
        kerberos-5i-read-only=KERBEROS_5I_READ_ONLY,
        kerberos-5i-read-write=KERBEROS_5I_READ_WRITE,
        kerberos-5p-read-only=KERBEROS_5P_READ_ONLY,
        kerberos-5p-read-write=KERBEROS_5P_READ_WRITE,
        squash-mode=SQUASH_MODE,anon-uid=ANON_UID`
  """)
  parser.add_argument(
      '--export-policy',
      type=arg_parsers.ArgDict(spec=export_policy_arg_spec),
      action='append',
      help=export_policy_help,
  )


def AddVolumeUnixPermissionsArg(parser):
  """Adds the Unix Permissions arg to the arg parser."""
  parser.add_argument(
      '--unix-permissions',
      type=str,
      help="""Unix permissions the mount point will be created with. \
Unix permissions are only applicable with NFS protocol only""",
  )


def GetVolumeSmbSettingsEnumFromArg(choice, messages):
  """Returns the Choice Enum for SMB Setting.

  Args:
    choice: The choice for SMB setting input as string
    messages: The messages module.

  Returns:
    The choice arg.
  """
  return arg_utils.ChoiceToEnum(
      choice=choice,
      enum_type=messages.Volume.SmbSettingsValueListEntryValuesEnum,
  )


def AddVolumeSmbSettingsArg(parser):
  """Adds the --smb-settings arg to the arg parser."""
  parser.add_argument(
      '--smb-settings',
      type=arg_parsers.ArgList(min_length=1, element_type=str),
      metavar='SMB_SETTING',
      help="""List of settings specific to SMB protocol \
for a Cloud NetApp Files Volume. \
Valid component values are:
  `ENCRYPT_DATA`, `BROWSABLE`, `CHANGE_NOTIFY`, `NON_BROWSABLE`,
  `OPLOCKS`, `SHOW_SNAPSHOT`, `SHOW_PREVIOUS_VERSIONS`,
  `ACCESS_BASED_ENUMERATION`, `CONTINUOUSLY_AVAILABLE`.""",
  )


def AddVolumeHourlySnapshotArg(parser):
  """Adds the --snapshot-hourly arg to the arg parser."""
  hourly_snapshot_arg_spec = {
      'snapshots-to-keep': float,
      'minute': float,
  }
  hourly_snapshot_help = """
  Make a snapshot every hour e.g. at 04:00, 05:20, 06:00
  """
  parser.add_argument(
      '--snapshot-hourly',
      type=arg_parsers.ArgDict(spec=hourly_snapshot_arg_spec),
      help=hourly_snapshot_help,
  )


def AddVolumeDailySnapshotArg(parser):
  """Adds the --snapshot-daily arg to the arg parser."""
  daily_snapshot_arg_spec = {
      'snapshots-to-keep': float,
      'minute': float,
      'hour': float,
  }
  daily_snapshot_help = """
  Make a snapshot every day e.g. at 06:00, 05:20, 23:50
  """
  parser.add_argument(
      '--snapshot-daily',
      type=arg_parsers.ArgDict(spec=daily_snapshot_arg_spec),
      help=daily_snapshot_help,
  )


def AddVolumeWeeklySnapshotArg(parser):
  """Adds the --snapshot-weekly arg to the arg parser."""
  weekly_snapshot_arg_spec = {
      'snapshots-to-keep': float,
      'minute': float,
      'hour': float,
      'day': str,
  }
  weekly_snapshot_help = """
  Make a snapshot every week e.g. at Monday 04:00, Wednesday 05:20,
  Sunday 23:50
  """
  parser.add_argument(
      '--snapshot-weekly',
      type=arg_parsers.ArgDict(spec=weekly_snapshot_arg_spec),
      help=weekly_snapshot_help,
  )


def AddVolumeMonthlySnapshotArg(parser):
  """Addss the --snapshot-monthly arg to the arg parser."""
  monthly_snapshot_arg_spec = {
      'snapshots-to-keep': float,
      'minute': float,
      'hour': float,
      'day': str,
  }
  monthly_snapshot_help = """
  Make a snapshot once a month e.g. at 2nd 04:00, 7th 05:20, 24th 23:50
  """
  parser.add_argument(
      '--snapshot-monthly',
      type=arg_parsers.ArgDict(spec=monthly_snapshot_arg_spec),
      help=monthly_snapshot_help,
  )


def AddVolumeSnapReserveArg(parser):
  """Adds the --snap-reserve arg to the arg parser."""
  action = actions.DeprecationAction(
      'snap-reserve', warn='The {flag_name} option is deprecated', removed=False
  )
  parser.add_argument(
      '--snap-reserve',
      type=float,
      help="""The percentage of volume storage reserved for snapshot storage.
      The default value for this is 0 percent""",
      action=action,
  )


def AddVolumeSnapshotDirectoryArg(parser):
  """Adds the --snapshot-directory arg to the arg parser."""
  parser.add_argument(
      '--snapshot-directory',
      type=arg_parsers.ArgBoolean(
          truthy_strings=netapp_util.truthy, falsey_strings=netapp_util.falsey
      ),
      default='true',
      help="""Snapshot Directory if enabled (true) makes the Volume
            contain a read-only .snapshot directory which provides access
            to each of the volume's snapshots
          """,
  )


def GetVolumeSecurityStyleEnumFromArg(choice, messages):
  """Returns the Choice Enum for Security style.

  Args:
    choice: The choice for Security style input as string
    messages: The messages module.

  Returns:
    The choice arg.
  """
  return arg_utils.ChoiceToEnum(
      choice=choice, enum_type=messages.Volume.SecurityStyleValueValuesEnum
  )


def AddVolumeSecurityStyleArg(parser, messages):
  """Adds the --security-style arg to the arg parser."""
  security_style_arg = arg_utils.ChoiceEnumMapper(
      '--security-style',
      messages.Volume.SecurityStyleValueValuesEnum,
      help_str="""The security style of the Volume. This can either be
          UNIX or NTFS.
        """,
      custom_mappings={
          'UNIX': ('unix', """UNIX security style for Volume"""),
          'NTFS': ('ntfs', """NTFS security style for Volume."""),
      },
      default='SECURITY_STYLE_UNSPECIFIED',
  )
  security_style_arg.choice_arg.AddToParser(parser)


def AddVolumeEnableKerberosArg(parser):
  """Adds the --enable-kerberos arg to the arg parser."""
  parser.add_argument(
      '--enable-kerberos',
      type=arg_parsers.ArgBoolean(
          truthy_strings=netapp_util.truthy, falsey_strings=netapp_util.falsey
      ),
      help="""Boolean flag indicating whether Volume is a kerberos Volume or not""",
  )


def AddVolumeEnableLdapArg(parser):
  """Adds the --enable-ladp arg to the arg parser."""
  parser.add_argument(
      '--enable-ldap',
      type=arg_parsers.ArgBoolean(
          truthy_strings=netapp_util.truthy, falsey_strings=netapp_util.falsey
      ),
      help="""Boolean flag indicating whether Volume is a NFS LDAP Volume or not""",
  )


def AddVolumeForceArg(parser):
  """Adds the --force arg to the arg parser."""
  parser.add_argument(
      '--force',
      action='store_true',
      help="""Forces the deletion of a volume and its child resources, such as snapshots.""",
  )


def AddVolumeRevertSnapshotArg(parser, required=True):
  """Adds the --snapshot arg to the arg parser."""
  concept_parsers.ConceptParser.ForResource(
      '--snapshot',
      flags.GetSnapshotResourceSpec(source_snapshot_op=True, positional=False),
      required=required,
      flag_name_overrides={'location': '', 'volume': ''},
      group_help='The Snapshot to revert the Volume back to.',
  ).AddToParser(parser)


def AddVolumeSourceSnapshotArg(parser):
  """Adds the --source-snapshot arg to the arg parser."""
  concept_parsers.ConceptParser.ForResource(
      '--source-snapshot',
      flags.GetSnapshotResourceSpec(source_snapshot_op=True, positional=False),
      flag_name_overrides={'location': '', 'volume': ''},
      group_help='The source Snapshot to create the Volume from.',
  ).AddToParser(parser)


def AddVolumeSourceBackupArg(parser):
  """Adds the --source-backup arg to the arg parser."""
  concept_parsers.ConceptParser.ForResource(
      '--source-backup',
      flags.GetBackupResourceSpec(positional=False),
      flag_name_overrides={'location': ''},
      group_help='The source Backup to create the Volume from.',
  ).AddToParser(parser)


def GetVolumeRestrictedActionsEnumFromArg(choice, messages):
  """Returns the Choice Enum for Restricted Actions.

  Args:
      choice: The choice for restricted actions input as string.
      messages: The messages module.

  Returns:
      the Restricted Actions enum.
  """
  return arg_utils.ChoiceToEnum(
      choice=choice,
      enum_type=messages.Volume.RestrictedActionsValueListEntryValuesEnum,
  )


def AddVolumeRestrictedActionsArg(parser):
  """Adds the --restricted-actions arg to the arg parser."""
  parser.add_argument(
      '--restricted-actions',
      type=arg_parsers.ArgList(min_length=1, element_type=str),
      metavar='RESTRICTED_ACTION',
      help="""Actions to be restricted for a volume. \
Valid restricted action options are:
          'DELETE'.""",
  )


def GetOsTypeEnumFromArg(choice, messages):
  """Returns the Choice Enum for OS Type.

  Args:
    choice: The choice for OS Type input as string.
    messages: The messages module.

  Returns:
    the OS Type enum.
  """

  return arg_utils.ChoiceToEnum(
      choice=choice,
      enum_type=messages.BlockDevice.OsTypeValueValuesEnum
  )


def AddVolumeBackupConfigArg(parser):
  """Adds the --backup-config arg to the arg parser."""
  backup_config_arg_spec = {
      'backup-policies': arg_parsers.ArgList(
          min_length=1, element_type=str, custom_delim_char='#'
      ),
      'backup-vault': str,
      'enable-scheduled-backups': arg_parsers.ArgBoolean(
          truthy_strings=netapp_util.truthy, falsey_strings=netapp_util.falsey
      ),
  }
  backup_config_help = textwrap.dedent("""\
    Backup Config contains backup related config on a volume.

        Backup Config will have the following format
        `--backup-config=backup-policies=BACKUP_POLICIES,
        backup-vault=BACKUP_VAULT_NAME,
        enable-scheduled-backups=ENABLE_SCHEDULED_BACKUPS

    backup-policies is a pound-separated (#) list of backup policy names, backup-vault can include
    a single backup-vault resource name, and enable-scheduled-backups is a Boolean value indicating
    whether or not scheduled backups are enabled on the volume.
  """)
  parser.add_argument(
      '--backup-config',
      type=arg_parsers.ArgDict(spec=backup_config_arg_spec),
      help=backup_config_help,
  )


def AddVolumeLargeCapacityArg(parser):
  """Adds the --large-capacity arg to the arg parser."""
  parser.add_argument(
      '--large-capacity',
      type=arg_parsers.ArgBoolean(
          truthy_strings=netapp_util.truthy, falsey_strings=netapp_util.falsey
      ),
      help="""Boolean flag indicating whether Volume is a large capacity Volume or not""",
  )


def AddVolumeMultipleEndpointsArg(parser):
  """Adds the --multiple-endpoints arg to the arg parser."""
  parser.add_argument(
      '--multiple-endpoints',
      type=arg_parsers.ArgBoolean(
          truthy_strings=netapp_util.truthy, falsey_strings=netapp_util.falsey
      ),
      help="""Boolean flag indicating whether Volume is a multiple endpoints Volume or not""",
  )


def AddVolumeLargeCapacityConfigArg(parser):
  """Adds the --large-capacity-config arg to the arg parser."""
  large_capacity_config_arg_spec = {
      'constituent-count': int,
  }
  large_capacity_config_help = textwrap.dedent("""\
      Large Capacity Config contains configuration for large capacity volumes.

      Large Capacity Config has the following format:
      `--large-capacity-config=constituent-count=CONSTITUENT_COUNT`
      `--large-capacity-config`

      *constituent-count*::: (optional) The number of constituents for a large capacity volume.
  """)
  parser.add_argument(
      '--large-capacity-config',
      type=arg_parsers.ArgDict(spec=large_capacity_config_arg_spec),
      nargs='?',
      const={},
      help=large_capacity_config_help,
      hidden=True,
  )


def AddVolumeBlockDevicesArg(parser, messages):
  """Adds the --block-devices arg to the arg parser."""
  block_device_arg_spec = {
      'name': str,
      'host-groups': arg_parsers.ArgList(
          min_length=1, element_type=str, custom_delim_char='#'),
      'os-type': messages.BlockDevice.OsTypeValueValuesEnum,
      'size-gib': int,
  }
  block_devices_help = textwrap.dedent("""\
    A block device to be created with the volume.

    This flag can be repeated to specify multiple block devices.

    The following keys are available:
    *name*::: A user-defined name for the block device.
    *host-groups*::: A comma-separated list of host groups that can mount the block volume.
    *os-type*::: The OS type of the volume. Allowed values are `OS_TYPE_UNSPECIFIED`, `LINUX`, `WINDOWS`.
    *size-gib*::: The size of the block device in GiB. Note that this value is ignored during volume creation and is system-managed.
  """)
  parser.add_argument(
      '--block-devices',
      type=arg_parsers.ArgDict(
          spec=block_device_arg_spec),
      action='append',
      help=block_devices_help,
  )


def AddVolumeTieringPolicyArg(parser, messages, release_track):
  """Adds the --tiering-policy arg to the arg parser."""
  if (release_track == calliope_base.ReleaseTrack.BETA or
      release_track == calliope_base.ReleaseTrack.ALPHA):
    tiering_policy_arg_spec = {
        'tier-action': messages.TieringPolicy.TierActionValueValuesEnum,
        'cooling-threshold-days': int,
        'enable-hot-tier-bypass-mode': arg_parsers.ArgBoolean(
            truthy_strings=netapp_util.truthy,
            falsey_strings=netapp_util.falsey,
        ),
    }
  else:
    tiering_policy_arg_spec = {
        'tier-action': messages.TieringPolicy.TierActionValueValuesEnum,
        'cooling-threshold-days': int,
    }
  tiering_policy_help = textwrap.dedent("""\
      Tiering Policy contains auto tiering policy on a volume.

      Tiering Policy will have the following format
      --tiering-policy=tier-action=TIER_ACTION,
      cooling-threshold-days=COOLING_THRESHOLD_DAYS

      tier-action is an enum, supported values are ENABLED or PAUSED,
cooling-threshold-days is an integer represents time in days to mark the
volume's data block as cold and make it eligible for tiering,
can be range from 7-183. Default is 31.
  """)
  parser.add_argument(
      '--tiering-policy',
      type=arg_parsers.ArgDict(spec=tiering_policy_arg_spec),
      metavar='tier-action=ENABLED|PAUSED',
      help=tiering_policy_help,
  )


def AddVolumeHybridReplicationParametersArg(
    parser, messages, release_track=calliope_base.ReleaseTrack.GA, hidden=False
):
  """Adds the --hybrid-replication-parameters arg to the arg parser."""
  del release_track
  hybrid_replication_parameters_arg_spec = {
      'replication': str,
      'peer-volume-name': str,
      'peer-cluster-name': str,
      'peer-svm-name': str,
      'peer-ip-addresses': arg_parsers.ArgList(
          min_length=1, element_type=str, custom_delim_char='#'
      ),
      'cluster-location': str,
      'description': str,
      'replication-schedule': (
          messages.HybridReplicationParameters.ReplicationScheduleValueValuesEnum
      ),
      'hybrid-replication-type': (
          messages.HybridReplicationParameters.HybridReplicationTypeValueValuesEnum
      ),
      'large-volume-constituent-count': int,
      'labels': arg_parsers.ArgList(
          min_length=1, element_type=str, custom_delim_char='#'
      ),
  }

  hybrid_replication_parameters_help = textwrap.dedent("""\
  Hybrid Replication Parameters contains hybrid replication parameters on a volume.

      Hybrid Replication Parameters will have the following format
      --hybrid-replication-parameters=replication=REPLICATION,
      peer-volume-name=PEER_VOLUME_NAME,
      peer-cluster-name=PEER_CLUSTER_NAME,
      peer-svm-name=PEER_SVM_NAME,
      peer-ip-addresses=[PEER-IP-ADDRESS1#PEER-IP-ADDRESS2#...],
      cluster-location=CLUSTER_LOCATION,
      description=DESCRIPTION,
      replication-schedule=REPLICATION_SCHEDULE,
      hybrid-replication-type=HYBRID_REPLICATION_TYPE,
      large-volume-constituent-count=LARGE_VOLUME_CONSTITUENT_COUNT,
      labels=[KEY1:VALUE1#KEY2:VALUE2#...],

  replication is the desired name for the replication of the volume,
  peer-volume-name is the name of the user's local source volume,
  peer-cluster-name is the name of the user's local source cluster,
  peer-svm-name is the name of the user's local source vserver svm,
  peer-ip-addresses is a ampersand-separated(#) list of ip addresses,
  cluster-location is the name of the source cluster location,
  description is the description of the replication,
  replication-schedule is the schedule of corresponding hybrid replication
  created, hybrid-replication-type is the hybrid replication type of the
  corresponding hybrid replication created, large-volume-constituent-count
  is the number of constituent volumes in the large volume, and labels is an
  hashtag-separated(#) key value pair of labels with key and value separated
  by colon(:) for the replication.
      """)
  parser.add_argument(
      '--hybrid-replication-parameters',
      type=arg_parsers.ArgDict(spec=hybrid_replication_parameters_arg_spec),
      help=hybrid_replication_parameters_help,
      hidden=hidden,
  )


def AddVolumeThroughputMibpsArg(parser):
  """Adds the --throughput-mibps arg to the arg parser."""
  parser.add_argument(
      '--throughput-mibps',
      type=float,
      help='The desired throughput of the volume in MiB/s.',
  )


def AddVolumeCacheParametersArg(parser, hidden=False):
  """Adds the --cache-parameters arg to the arg parser."""
  cache_parameters_arg_spec = {
      'peer-volume-name': str,
      'peer-cluster-name': str,
      'peer-svm-name': str,
      'peer-ip-addresses': arg_parsers.ArgList(
          min_length=1, element_type=str, custom_delim_char='#'
      ),
      'enable-global-file-lock': arg_parsers.ArgBoolean(
          truthy_strings=netapp_util.truthy, falsey_strings=netapp_util.falsey
      ),
      'cache-config': arg_parsers.ArgList(
          element_type=arg_parsers.ArgDict(), custom_delim_char='#'
      ),
  }
  cache_parameters_help = textwrap.dedent("""\
  Cache Parameters contains cache parameters of a volume.

      Cache Parameters will have the following format
      `--cache-parameters=peer-volume-name=PEER_VOLUME_NAME,
        peer-cluster-name=PEER_CLUSTER_NAME,
        peer-svm-name=PEER_SVM_NAME,
        peer-ip-addresses=[PEER-IP-ADDRESS1#PEER-IP-ADDRESS2#...],
        enable-global-file-lock=ENABLE_GLOBAL_FILE_LOCK,
        cache-config=CACHE_CONFIG`

      *peer-volume-name*::: Name of the user's local source volume
      *peer-cluster-name*::: Name of the user's local source cluster
      *peer-svm-name*::: Name of the user's local source vserver svm
      *peer-ip-addresses*::: Hashtag-separated(#) list of IP addresses
      *enable-global-file-lock*::: If true, enable global file lock
      *cache-config*::: Cache-config as a hashtag-separated(#) list of key-value pairs
  """)
  parser.add_argument(
      '--cache-parameters',
      type=arg_parsers.ArgDict(spec=cache_parameters_arg_spec),
      help=cache_parameters_help,
      hidden=hidden,
  )


def AddVolumeCachePrePopulateArg(parser, hidden=False):
  """Adds the --cache-pre-populate arg to the arg parser."""
  cache_pre_populate_arg_spec = {
      'path-list': arg_parsers.ArgList(
          min_length=1, element_type=str, custom_delim_char='#'
      ),
      'exclude-path-list': arg_parsers.ArgList(
          min_length=1, element_type=str, custom_delim_char='#'
      ),
      'recursion': arg_parsers.ArgBoolean(
          truthy_strings=netapp_util.truthy, falsey_strings=netapp_util.falsey
      ),
  }
  cache_pre_populate_help = textwrap.dedent("""\
      Cache Pre-populate contains cache pre-populate parameters of a volume.

      Cache Pre-populate will have the following format
      `--cache-pre-populate=path-list=PATH_LIST1#PATH_LIST2,
        exclude-path-list=EXCLUDE_PATH_LIST1#EXCLUDE_PATH_LIST2,
        recursion=RECURSION`

      *path-list*::: Hashtag-separated(#) list of paths to be pre-populated
      *exclude-path-list*::: Hashtag-separated(#) list of paths to be excluded from pre-population
      *recursion*::: Boolean value indicating pre-populate recursion.
  """)
  parser.add_argument(
      '--cache-pre-populate',
      type=arg_parsers.ArgDict(spec=cache_pre_populate_arg_spec),
      help=cache_pre_populate_help,
      hidden=hidden,
  )


def AddVolumeRestoreFileListArg(parser, required=True):
  """Adds the --file-list arg to the arg parser."""
  parser.add_argument(
      '--file-list',
      type=arg_parsers.ArgList(min_length=1, element_type=str),
      metavar='FILE_LIST',
      required=required,
      help="""List of files to be restored in the form of their absolute path as in source volume.""",
  )


def AddVolumeRestoreDestinationPathArg(parser, required=False):
  """Adds the --restore-destination-path arg to the arg parser."""
  parser.add_argument(
      '--restore-destination-path',
      type=str,
      required=required,
      help="""Name of the absolute directory path in the destination volume..""",
  )

## Helper functions to combine Volumes args / flags for gcloud commands #


def AddVolumeCreateArgs(parser, release_track):
  """Add args for creating a Volume."""
  concept_parsers.ConceptParser(
      [flags.GetVolumePresentationSpec('The Volume to create.')]
  ).AddToParser(parser)
  messages = netapp_api_util.GetMessagesModule(release_track=release_track)
  flags.AddResourceDescriptionArg(parser, 'Volume')
  flags.AddResourceCapacityArg(parser, 'Volume')
  AddVolumeAssociatedStoragePoolArg(parser)
  flags.AddResourceAsyncFlag(parser)
  AddVolumeProtocolsArg(parser)
  AddVolumeShareNameArg(parser)
  AddVolumeExportPolicyArg(parser, messages)
  AddVolumeUnixPermissionsArg(parser)
  AddVolumeSmbSettingsArg(parser)
  AddVolumeSourceSnapshotArg(parser)
  AddVolumeHourlySnapshotArg(parser)
  AddVolumeDailySnapshotArg(parser)
  AddVolumeWeeklySnapshotArg(parser)
  AddVolumeMonthlySnapshotArg(parser)
  AddVolumeSnapReserveArg(parser)
  AddVolumeSnapshotDirectoryArg(parser)
  AddVolumeSecurityStyleArg(parser, messages)
  AddVolumeEnableKerberosArg(parser)
  AddVolumeRestrictedActionsArg(parser)
  AddVolumeLargeCapacityArg(parser)
  AddVolumeMultipleEndpointsArg(parser)
  if release_track in [
      calliope_base.ReleaseTrack.BETA, calliope_base.ReleaseTrack.GA,
  ]:
    AddVolumeBackupConfigArg(parser)
    AddVolumeSourceBackupArg(parser)
  AddVolumeThroughputMibpsArg(parser)
  AddVolumeTieringPolicyArg(parser, messages, release_track)
  AddVolumeHybridReplicationParametersArg(parser, messages, release_track)
  AddVolumeCacheParametersArg(parser)
  AddVolumeCachePrePopulateArg(parser)
  AddVolumeBlockDevicesArg(parser, messages)
  labels_util.AddCreateLabelsFlags(parser)
  if release_track in [
      calliope_base.ReleaseTrack.ALPHA,
      calliope_base.ReleaseTrack.BETA,
  ]:
    AddVolumeLargeCapacityConfigArg(parser)


def AddVolumeDeleteArgs(parser):
  """Add args for deleting a Volume."""
  concept_parsers.ConceptParser(
      [flags.GetVolumePresentationSpec('The Volume to delete.')]
  ).AddToParser(parser)
  flags.AddResourceAsyncFlag(parser)
  AddVolumeForceArg(parser)


def AddVolumeUpdateArgs(parser, release_track):
  """Add args for updating a Volume."""
  concept_parsers.ConceptParser(
      [flags.GetVolumePresentationSpec('The Volume to update.')]
  ).AddToParser(parser)
  messages = netapp_api_util.GetMessagesModule(release_track=release_track)
  flags.AddResourceDescriptionArg(parser, 'Volume')
  flags.AddResourceCapacityArg(parser, 'Volume', required=False)
  AddVolumeAssociatedStoragePoolArg(parser, required=False)
  flags.AddResourceAsyncFlag(parser)
  AddVolumeProtocolsArg(parser, required=False)
  AddVolumeShareNameArg(parser, required=False)
  AddVolumeExportPolicyArg(parser, messages)
  AddVolumeUnixPermissionsArg(parser)
  AddVolumeSmbSettingsArg(parser)
  AddVolumeSourceSnapshotArg(parser)
  AddVolumeHourlySnapshotArg(parser)
  AddVolumeDailySnapshotArg(parser)
  AddVolumeWeeklySnapshotArg(parser)
  AddVolumeMonthlySnapshotArg(parser)
  AddVolumeSnapReserveArg(parser)
  AddVolumeSnapshotDirectoryArg(parser)
  AddVolumeSecurityStyleArg(parser, messages)
  AddVolumeEnableKerberosArg(parser)
  AddVolumeRestrictedActionsArg(parser)
  if release_track in [
      calliope_base.ReleaseTrack.BETA, calliope_base.ReleaseTrack.GA,
  ]:
    AddVolumeBackupConfigArg(parser)
    AddVolumeSourceBackupArg(parser)
  AddVolumeThroughputMibpsArg(parser)
  AddVolumeTieringPolicyArg(parser, messages, release_track)
  AddVolumeCacheParametersArg(parser)
  AddVolumeCachePrePopulateArg(parser)
  AddVolumeBlockDevicesArg(parser, messages)
  labels_util.AddUpdateLabelsFlags(parser)


def AddVolumeRestoreFromBackupArg(parser, required=True):
  """Adds the --backup arg to the arg parser."""
  concept_parsers.ConceptParser.ForResource(
      '--backup',
      flags.GetBackupResourceSpec(positional=False),
      required=required,
      flag_name_overrides={'location': ''},
      group_help='The Backup from which files are restored back to the Volume.',
  ).AddToParser(parser)
