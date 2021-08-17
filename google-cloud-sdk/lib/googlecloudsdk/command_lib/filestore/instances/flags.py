# -*- coding: utf-8 -*- #
# Copyright 2017 Google LLC. All Rights Reserved.
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
"""Flags and helpers for the Cloud Filestore instances commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.filestore import filestore_client
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.filestore import flags
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.command_lib.util.args import labels_util
from googlecloudsdk.command_lib.util.concepts import concept_parsers

INSTANCES_LIST_FORMAT = """\
    table(
      name.basename():label=INSTANCE_NAME:sort=1,
      name.segment(3):label=ZONE,
      tier,
      fileShares[0].capacityGb:label=CAPACITY_GB,
      fileShares[0].name:label=FILE_SHARE_NAME,
      networks[0].ipAddresses[0]:label=IP_ADDRESS,
      state,
      createTime.date()
    )"""

INSTANCES_LIST_FORMAT_ALPHA_BETA = """\
    table(
      name.basename():label=INSTANCE_NAME:sort=1,
      name.segment(3):label=LOCATION,
      tier,
      fileShares[0].capacityGb:label=CAPACITY_GB,
      fileShares[0].name:label=FILE_SHARE_NAME,
      networks[0].ipAddresses[0]:label=IP_ADDRESS,
      state,
      createTime.date()
    )"""

FILE_SHARE_ARG_SPEC = {
    'name':
        str,
    'capacity':
        arg_parsers.BinarySize(
            default_unit='GB',
            suggested_binary_size_scales=['GB', 'GiB', 'TB', 'TiB']),
    'nfs-export-options':
        list
}

FILE_TIER_TO_TYPE = {
    'TIER_UNSPECIFIED': 'BASIC',
    'STANDARD': 'BASIC',
    'PREMIUM': 'BASIC',
    'BASIC_HDD': 'BASIC',
    'BASIC_SSD': 'BASIC',
    'ENTERPRISE': 'ENTERPRISE',
    'HIGH_SCALE_SSD': 'HIGH SCALE'
}


def AddAsyncFlag(parser):
  help_text = """Return immediately, without waiting for the operation
  in progress to complete."""
  concepts.ResourceParameterAttributeConfig(name='async', help_text=help_text)
  base.ASYNC_FLAG.AddToParser(parser)


def GetTierType(instance_tier):
  tier_type = dict(FILE_TIER_TO_TYPE)
  return tier_type.get(instance_tier, 'BASIC')


def AddLocationArg(parser):
  parser.add_argument(
      '--location',
      required=False,
      help='Location of the Cloud Filestore instance/operation.')


def AddRegionArg(parser):
  parser.add_argument(
      '--region',
      required=False,
      help='Region of the Cloud Filestore instance.')


def AddDescriptionArg(parser):
  parser.add_argument(
      '--description', help='A description of the Cloud Filestore instance.')


def GetTierArg(messages, api_version):
  """Adds a --tier flag to the given parser.

  Args:
    messages: The messages module.
    api_version: filestore_client api version.

  Returns:
    the choice arg.
  """
  if ((api_version == filestore_client.ALPHA_API_VERSION) or
      (api_version == filestore_client.BETA_API_VERSION)):
    tier_arg = (
        arg_utils.ChoiceEnumMapper(
            '--tier',
            messages.Instance.TierValueValuesEnum,
            help_str="""The service tier for the Cloud Filestore instance.
         For more details, see:
         https://cloud.google.com/filestore/docs/instance-tiers """,
            custom_mappings={
                'STANDARD':
                    ('standard',
                     """Standard Filestore instance, An alias for BASIC_HDD.
                     Use BASIC_HDD instead whenever possible."""),
                'PREMIUM': ('premium',
                            """Premium Filestore instance, An alias for BASIC_SSD.
                            Use BASIC_SSD instead whenever possible."""),
                'BASIC_HDD':
                    ('basic-hdd', 'Performant NFS storage system using HDD.'),
                'BASIC_SSD':
                    ('basic-ssd', 'Performant NFS storage system using SSD.'),
                'ENTERPRISE':
                    ('enterprise', """ENTERPRISE instances offer the features\
                    and availability needed for mission-critical workloads."""),
                'HIGH_SCALE_SSD': (
                    'high-scale-ssd',
                    """NFS storage system with expanded capacity and performance\
                    scaling capabilities.""")
            },
            default='BASIC_HDD'))
  else:
    tier_arg = (
        arg_utils.ChoiceEnumMapper(
            '--tier',
            messages.Instance.TierValueValuesEnum,
            help_str='The service tier for the Cloud Filestore instance.',
            custom_mappings={
                'STANDARD': ('standard', 'Standard Filestore instance.'),
                'PREMIUM': ('premium', 'Premium Filestore instance.')
            },
            default='STANDARD'))
  return tier_arg


def AddNetworkArg(parser, api_version):
  """Adds a --network flag to the given parser.

  Args:
    parser: argparse parser.
    api_version: API version.
  """

  network_arg_spec = {}

  if api_version == filestore_client.ALPHA_API_VERSION or api_version == filestore_client.BETA_API_VERSION:
    network_arg_spec = {
        'name': str,
        'reserved-ip-range': str,
        'connect-mode': str,
    }

    network_help = """\
        Network configuration for a Cloud Filestore instance. Specifying
        `reserved-ip-range` and `connect-mode` is optional.
        *name*::: The name of the Google Compute Engine
        [VPC network](/compute/docs/networks-and-firewalls#networks) to which
        the instance is connected.
        *reserved-ip-range*::: The `reserved-ip-range` can have one of the
        following two types of values: a CIDR range value when using
        DIRECT_PEERING connect mode or an allocated IP address range
        (https://cloud.google.com/compute/docs/ip-addresses/reserve-static-internal-ip-address)
        when using PRIVATE_SERVICE_ACCESS connect mode. When the name of an
        allocated IP address range is specified, it must be one of the ranges
        associated with the private service access connection. When specified as
        a direct CIDR value, it must be a /29 CIDR block for Basic tier or a /24
        CIDR block for High Scale or Enterprise tier in one of the internal IP
        address ranges (https://www.arin.net/knowledge/address_filters.html)
        that identifies the range of IP addresses reserved for this instance.
        For example, 10.0.0.0/29 or 192.168.0.0/24. The range you specify can't
        overlap with either existing subnets or assigned IP address ranges for
        other Cloud Filestore instances in the selected VPC network.
        *connect-mode*::: Network connection mode used by instances.
        CONNECT_MODE must be one of: DIRECT_PEERING or PRIVATE_SERVICE_ACCESS.
    """
  else:
    network_arg_spec = {
        'name': str,
        'reserved-ip-range': str,
    }

    network_help = """\
      Network configuration for a Cloud Filestore instance. Specifying
      `reserved-ip-range` is optional.
      *name*::: The name of the Google Compute Engine
      [VPC network](/compute/docs/networks-and-firewalls#networks) to which the
      instance is connected.
      *reserved-ip-range*::: A /29 CIDR block in one of the
      [internal IP address ranges](https://www.arin.net/knowledge/address_filters.html)
      that identifies the range of IP addresses reserved for this
      instance. For example, 10.0.0.0/29 or 192.168.0.0/29. The range you
      specify can't overlap with either existing subnets or assigned IP address
      ranges for other Cloud Filestore instances in the selected VPC network.
      """

  parser.add_argument(
      '--network',
      type=arg_parsers.ArgDict(spec=network_arg_spec, required_keys=['name']),
      required=True,
      help=network_help)


def AddFileShareArg(parser,
                    api_version,
                    include_snapshot_flags=False,
                    include_backup_flags=False,
                    required=True):
  """Adds a --file-share flag to the given parser.

  Args:
    parser: argparse parser.
    api_version: filestore_client api version.
    include_snapshot_flags: bool, whether to include --source-snapshot flags.
    include_backup_flags: bool, whether to include --source-backup flags.
    required: bool, passthrough to parser.add_argument.
  """
  file_share_help = {
      filestore_client.V1_API_VERSION:
          """\
File share configuration for an instance.  Specifying both `name` and `capacity`
is required.

*capacity*::: The desired capacity of the volume. The capacity must be a whole
number followed by a capacity unit such as ``TB'' for terabyte. If no capacity
unit is specified, GB is assumed. The minimum capacity for a standard instance
is 0.5TB. The minimum capacity for a premium instance is 0.5TB.

*name*::: The desired logical name of the volume.

*nfs-export-options*::: The NfsExportOptions for the Cloud Filestore instance file share.
Configuring NfsExportOptions is optional.
Use the `--flags-file` flag to specify the path to a JSON or YAML configuration file that contains the required NfsExportOptions flags.

*ip-ranges*::: A list of IPv4 addresses or CIDR ranges that are allowed to mount the file share.
IPv4 addresses format: {octet 1}.{octet 2}.{octet 3}.{octet 4}.
CIDR range format: {octet 1}.{octet 2}.{octet 3}.{octet 4}/{mask size}.
Overlapping IP ranges, even across NfsExportOptions, are not allowed and will return an error.
The limit of IP ranges/addresses for each FileShareConfig among all NfsExportOptions is 64 per instance.

*access-mode*::: The type of access allowed for the specified IP-addresses or CIDR ranges.
READ_ONLY: Allows only read requests on the exported file share.
READ_WRITE: Allows both read and write requests on the exported file share.
The default setting is READ_WRITE.

*squash-mode*::: Enables or disables root squash for the specified
IP addresses or CIDR ranges.
NO_ROOT_SQUASH: Disables root squash to allow root access on the exported file share.
ROOT_SQUASH. Enables root squash to remove root access on the exported file share.
The default setting is NO_ROOT_SQUASH.

*anon_uid*::: An integer that represents the user ID of anonymous users.
Anon_uid may only be set when squash_mode is set to ROOT_SQUASH.
If NO_ROOT_SQUASH is specified, an error will be returned.
The default value is 65534.

*anon_gid*::: An integer that represents the group ID of anonymous groups.
Anon_gid may only be set when squash_mode is set to ROOT_SQUASH.
If NO_ROOT_SQUASH is specified, an error will be returned.
The default value is 65534.
""",
      filestore_client.ALPHA_API_VERSION:
          """
File share configuration for an instance. Specifying both `name` and `capacity`
is required.

*capacity*::: The desired capacity of the volume in GB or TB units. If no capacity
unit is specified, GB is assumed. Acceptable instance capacities for each tier are as follows:
* BASIC_HDD: 1TB-63.9TB in 1GB increments or its multiples.
* BASIC_SSD: 2.5TB-63.9TB in 1GB increments or its multiples.
* HIGH_SCALE_SSD: 60TB-320TB in 10TB increments or its multiples.
* ENTERPRISE: 1TB-10TB in 256GiB increments or its multiples.

*name*::: The desired logical name of the volume.

*nfs-export-options*::: The NfsExportOptions for the Cloud Filestore instance file share.
Configuring NfsExportOptions is optional.
Use the `--flags-file` flag to specify the path to a JSON or YAML configuration file that contains the required NfsExportOptions flags.

*ip-ranges*::: A list of IPv4 addresses or CIDR ranges that are allowed to mount the file share.
IPv4 addresses format: {octet 1}.{octet 2}.{octet 3}.{octet 4}.
CIDR range format: {octet 1}.{octet 2}.{octet 3}.{octet 4}/{mask size}.
Overlapping IP ranges, even across NfsExportOptions, are not allowed and will return an error.
The limit of IP ranges/addresses for each FileShareConfig among all NfsExportOptions is 64 per instance.

*access-mode*::: The type of access allowed for the specified IP-addresses or CIDR ranges.
READ_ONLY: Allows only read requests on the exported file share.
READ_WRITE: Allows both read and write requests on the exported file share.
The default setting is READ_WRITE.

*squash-mode*::: Enables or disables root squash for the specified
IP addresses or CIDR ranges.
NO_ROOT_SQUASH: Disables root squash to allow root access on the exported file share.
ROOT_SQUASH. Enables root squash to remove root access on the exported file share.
The default setting is NO_ROOT_SQUASH.

*anon_uid*::: An integer that represents the user ID of anonymous users.
Anon_uid may only be set when squash_mode is set to ROOT_SQUASH.
If NO_ROOT_SQUASH is specified, an error will be returned.
The default value is 65534.

*anon_gid*::: An integer that represents the group ID of anonymous groups.
Anon_gid may only be set when squash_mode is set to ROOT_SQUASH.
If NO_ROOT_SQUASH is specified, an error will be returned.
The default value is 65534.
""",
      filestore_client.BETA_API_VERSION:
          """
File share configuration for an instance. Specifying both `name` and `capacity`
is required.

*capacity*::: The desired capacity of the volume in GB or TB units. If no capacity
unit is specified, GB is assumed. Acceptable instance capacities for each tier are as follows:
* BASIC_HDD: 0.5TB-63.9TB in 1GB increments or its multiples.
* BASIC_SSD: 0.5TB-63.9TB in 1GB increments or its multiples.
* HIGH_SCALE_SSD: 60TB-320TB in 10TB increments or its multiples.

*name*::: The desired logical name of the volume.

*nfs-export-options*::: The NfsExportOptions for the Cloud Filestore instance file share.
Configuring NfsExportOptions is optional.
Use the `--flags-file` flag to specify the path to a JSON or YAML configuration file that contains the required NfsExportOptions flags.

*ip-ranges*::: A list of IPv4 addresses or CIDR ranges that are allowed to mount the file share.
IPv4 addresses format: {octet 1}.{octet 2}.{octet 3}.{octet 4}.
CIDR range format: {octet 1}.{octet 2}.{octet 3}.{octet 4}/{mask size}.
Overlapping IP ranges, even across NfsExportOptions, are not allowed and will return an error.
The limit of IP ranges/addresses for each FileShareConfig among all NfsExportOptions is 64 per instance.

*access-mode*::: The type of access allowed for the specified IP-addresses or CIDR ranges.
READ_ONLY: Allows only read requests on the exported file share.
READ_WRITE: Allows both read and write requests on the exported file share.
The default setting is READ_WRITE.

*squash-mode*::: Enables or disables root squash for the specified
IP addresses or CIDR ranges.
NO_ROOT_SQUASH: Disables root squash to allow root access on the exported file share.
ROOT_SQUASH. Enables root squash to remove root access on the exported file share.
The default setting is NO_ROOT_SQUASH.

*anon_uid*::: An integer that represents the user ID of anonymous users.
Anon_uid may only be set when squash_mode is set to ROOT_SQUASH.
If NO_ROOT_SQUASH is specified, an error will be returned.
The default value is 65534.

*anon_gid*::: An integer that represents the group ID of anonymous groups.
Anon_gid may only be set when squash_mode is set to ROOT_SQUASH.
If NO_ROOT_SQUASH is specified, an error will be returned.
The default value is 65534.
"""
  }
  source_snapshot_help = """\

*source-snapshot*::: The name of the snapshot to restore from. Supported for BASIC instances only.

*source-snapshot-region*::: The region of the source snapshot. If
unspecified, it is assumed that the Filestore snapshot is local and
instance-zone will be used.

"""
  source_backup_help = """\

*source-backup*::: The name of the backup to restore from.

*source-backup-region*::: The region of the source backup.

"""

  spec = FILE_SHARE_ARG_SPEC.copy()
  if include_backup_flags:
    spec['source-backup'] = str
    spec['source-backup-region'] = str
  if include_snapshot_flags:
    spec['source-snapshot'] = str
    spec['source-snapshot-region'] = str

  file_share_help = file_share_help[api_version]
  parser.add_argument(
      '--file-share',
      type=arg_parsers.ArgDict(spec=spec, required_keys=['name', 'capacity']),
      required=required,
      help=file_share_help +
      (source_snapshot_help if include_snapshot_flags else '') +
      (source_backup_help if include_backup_flags else ''))


def AddInstanceCreateArgs(parser, api_version):
  """Add args for creating an instance."""
  concept_parsers.ConceptParser([
      flags.GetInstancePresentationSpec('The instance to create.')
  ]).AddToParser(parser)
  AddDescriptionArg(parser)
  AddLocationArg(parser)
  if ((api_version == filestore_client.ALPHA_API_VERSION) or
      (api_version == filestore_client.BETA_API_VERSION)):
    AddRegionArg(parser)
  AddAsyncFlag(parser)
  labels_util.AddCreateLabelsFlags(parser)
  AddNetworkArg(parser, api_version)
  messages = filestore_client.GetMessages(version=api_version)
  GetTierArg(messages, api_version).choice_arg.AddToParser(parser)
  AddFileShareArg(
      parser,
      api_version,
      include_snapshot_flags=(
          api_version == filestore_client.ALPHA_API_VERSION),
      include_backup_flags=True)


def AddInstanceUpdateArgs(parser, api_version):
  """Add args for updating an instance."""
  concept_parsers.ConceptParser([
      flags.GetInstancePresentationSpec('The instance to update.')
  ]).AddToParser(parser)
  AddDescriptionArg(parser)
  AddLocationArg(parser)
  if ((api_version == filestore_client.ALPHA_API_VERSION) or
      (api_version == filestore_client.BETA_API_VERSION)):
    AddRegionArg(parser)
  AddAsyncFlag(parser)
  labels_util.AddUpdateLabelsFlags(parser)
  AddFileShareArg(
      parser,
      api_version,
      include_snapshot_flags=(
          api_version == filestore_client.ALPHA_API_VERSION),
      required=False)
