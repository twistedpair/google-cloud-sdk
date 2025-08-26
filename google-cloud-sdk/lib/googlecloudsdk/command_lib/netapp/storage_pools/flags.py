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
"""Flags and helpers for the Cloud NetApp Files Storage Pools commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.netapp import util as netapp_api_util
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.netapp import flags
from googlecloudsdk.command_lib.netapp import util as netapp_util
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.command_lib.util.args import labels_util
from googlecloudsdk.command_lib.util.concepts import concept_parsers


STORAGE_POOLS_LIST_FORMAT = """\
    table(
        name.basename():label=STORAGE_POOL_NAME:sort=1,
        name.segment(3):label=LOCATION,
        serviceLevel,
        capacityGib,
        network,
        state,
        volumeCapacityGib,
        type
    )"""

STORAGE_POOLS_LIST_FORMAT_GA = """\
    table(
        name.basename():label=STORAGE_POOL_NAME:sort=1,
        name.segment(3):label=LOCATION,
        serviceLevel,
        capacityGib,
        network,
        state,
        volumeCapacityGib
    )"""

## Helper functions to add args / flags for Storage Pools gcloud commands ##


def GetStoragePoolServiceLevelArg(messages, required=True):
  """Adds a --service-level arg to the given parser.

  Args:
    messages: The messages module.
    required: bool, whether choice arg is required or not

  Returns:
    the choice arg.
  """
  custom_mappings = {
      'PREMIUM': (
          'premium',
          """
                          Premium Service Level for Cloud NetApp Storage Pool.
                          The Premium Service Level has a throughput per GiB of
                          allocated volume size of 64 KiB/s.""",
      ),
      'EXTREME': (
          'extreme',
          """
                          Extreme Service Level for Cloud NetApp Storage Pool.
                          The Extreme Service Level has a throughput per GiB of
                          allocated volume size of 128 KiB/s.""",
      ),
      'STANDARD': (
          'standard',
          """
                          Standard Service Level for Cloud NetApp Storage Pool.
                          The Standard Service Level has a throughput per GiB of
                          allocated volume size of 16 KiB/s.""",
      ),
      'FLEX': (
          'flex',
          """
                          Flex Service Level for Cloud NetApp Storage Pool.
                          The Flex Service Level has a throughput per GiB of
                          allocated volume size of 16 KiB/s.""",
      ),
  }
  service_level_arg = arg_utils.ChoiceEnumMapper(
      '--service-level',
      messages.StoragePool.ServiceLevelValueValuesEnum,
      help_str="""The service level for the Cloud NetApp Storage Pool.
       For more details, see:
       https://cloud.google.com/netapp/volumes/docs/configure-and-use/storage-pools/overview#service_levels
        """,
      custom_mappings=custom_mappings,
      required=required,
  )
  return service_level_arg


def GetDirectoryServiceTypeEnumFromArg(choice, messages):
  """Returns the Choice Enum for Directory Service Type.

  Args:
    choice: The choice for directory service type as string
    messages: The messages module.

  Returns:
    the directory service type enum.
  """
  return arg_utils.ChoiceToEnum(
      choice=choice,
      enum_type=messages.ValidateDirectoryServiceRequest.DirectoryServiceTypeValueValuesEnum,
  )


def GetStoragePoolQosTypeArg(messages):
  """Adds the Qos Type arg to the arg parser."""
  qos_type_arg = arg_utils.ChoiceEnumMapper(
      '--qos-type',
      messages.StoragePool.QosTypeValueValuesEnum,
      help_str="""Quality of service (QoS) type for the Storage Pool.""",
  )
  return qos_type_arg


def GetStoragePoolTypeEnumFromArg(choice, messages):
  """Returns the Choice Enum for StoragePoolType."""
  return arg_utils.ChoiceToEnum(
      choice=choice,
      enum_type=messages.StoragePool.TypeValueValuesEnum
  )


def AddStoragePoolTypeArg(parser, messages):
  """Adds the --type arg to the arg parser for Storage Pools."""
  type_arg = arg_utils.ChoiceEnumMapper(
      '--type',
      messages.StoragePool.TypeValueValuesEnum,
      help_str='The type of the Storage Pool. `FILE` pools support file-based '
               'volumes only. `UNIFIED` pools support both file and block '
               'volumes.',
      hidden=True,
      custom_mappings={
          'FILE': ('file', 'File-based volumes only (default).'),
          'UNIFIED': ('unified', 'Both file and block volumes.'),
      })
  type_arg.choice_arg.AddToParser(parser)


def AddStoragePoolServiceLevelArg(
    parser, messages, required=False
):
  GetStoragePoolServiceLevelArg(
      messages, required=required
  ).choice_arg.AddToParser(parser)


def AddStoragePoolAsyncFlag(parser):
  help_text = """Return immediately, without waiting for the operation
  in progress to complete."""
  concepts.ResourceParameterAttributeConfig(name='async', help_text=help_text)
  base.ASYNC_FLAG.AddToParser(parser)


def AddStoragePoolNetworkArg(parser, required=True):
  """Adds a --network arg to the given parser.

  Args:
    parser: argparse parser.
    required: bool whether arg is required or not
  """

  network_arg_spec = {
      'name': str,
      'psa-range': str,
  }

  network_help = """\
        Network configuration for a Cloud NetApp Files Storage Pool. Specifying
        `psa-range` is optional.
        *name*::: The name of the Google Compute Engine
        [VPC network](/compute/docs/networks-and-firewalls#networks) to which
        the volume is connected. Short-form (VPC network ID) or long-form
        (full VPC network name: projects/PROJECT/locations/LOCATION/networks/NETWORK) are both
        accepted, but please use the long-form when attempting to create a Storage Pool using a shared VPC.
        *psa-range*::: This field is not implemented. The values provided in
        this field are ignored.
  """

  parser.add_argument(
      '--network',
      type=arg_parsers.ArgDict(spec=network_arg_spec, required_keys=['name']),
      required=required,
      help=network_help)


def AddStoragePoolActiveDirectoryArg(parser):
  """Adds a --active-directory arg to the given parser."""
  concept_parsers.ConceptParser.ForResource(
      '--active-directory',
      flags.GetActiveDirectoryResourceSpec(),
      'The Active Directory to attach to the Storage Pool.',
      flag_name_overrides={'location': ''}).AddToParser(parser)


def AddStoragePoolKmsConfigArg(parser):
  """Adds a --kms-config arg to the given parser."""
  concept_parsers.ConceptParser.ForResource(
      '--kms-config',
      flags.GetKmsConfigResourceSpec(),
      'The KMS config to attach to the Storage Pool.',
      flag_name_overrides={'location': ''}).AddToParser(parser)


def AddStoragePoolEnableLdapArg(parser):
  """Adds the --enable-ladp arg to the given parser."""
  parser.add_argument(
      '--enable-ldap',
      type=arg_parsers.ArgBoolean(
          truthy_strings=netapp_util.truthy, falsey_strings=netapp_util.falsey),
      help="""Boolean flag indicating whether Storage Pool is a NFS LDAP Storage Pool or not"""
  )


def AddStoragePoolAllowAutoTieringArg(parser):
  """Adds the --allow-auto-tiering arg to the given parser."""
  parser.add_argument(
      '--allow-auto-tiering',
      type=arg_parsers.ArgBoolean(
          truthy_strings=netapp_util.truthy, falsey_strings=netapp_util.falsey),
      help="""Boolean flag indicating whether Storage Pool is allowed to use auto-tiering""",
  )


def AddStoragePoolZoneArg(parser):
  """Adds the Zone arg to the arg parser."""
  parser.add_argument(
      '--zone',
      type=str,
      help="""String indicating active zone of the Storage Pool""",
  )


def AddStoragePoolReplicaZoneArg(parser):
  """Adds the Replica Zone arg to the arg parser."""
  parser.add_argument(
      '--replica-zone',
      type=str,
      help="""String indicating replica zone for the Storage Pool""",
  )


def AddStoragePoolDirectoryServiceTypeArg(parser):
  """Adds the Directory Service Type arg to the arg parser."""
  parser.add_argument(
      '--directory-service-type',
      type=str,
      help="""String indicating directory service type for the Storage Pool""",
  )


def AddStoragePoolCustomPerformanceEnabledArg(parser):
  """Adds the Custom Performance Enabled arg to the arg parser."""
  parser.add_argument(
      '--custom-performance-enabled',
      type=arg_parsers.ArgBoolean(
          truthy_strings=netapp_util.truthy, falsey_strings=netapp_util.falsey
      ),
      help="""Boolean flag indicating whether Storage Pool is a custom performance Storage Pool or not""",
  )


def AddStoragePoolTotalThroughputArg(parser):
  """Adds the Total Throughput arg to the arg parser."""
  parser.add_argument(
      '--total-throughput',
      type=arg_parsers.BinarySize(
          default_unit='MiB/s',
          suggested_binary_size_scales=['MiB/s', 'GiB/s'],
          type_abbr='B/s',
      ),
      help="""The total throughput of the Storage Pool in MiB/s or GiB/s units.
              If no throughput unit is specified, MiB/s is assumed.""",
  )


def AddStoragePoolTotalIopsArg(parser):
  """Adds the Total IOPS arg to the arg parser."""
  parser.add_argument(
      '--total-iops',
      type=int,
      help="""Integer indicating total IOPS of the Storage Pool""",
  )


def AddStoragePoolHotTierSizeArg(parser):
  """Adds the Hot Tier Size arg to the arg parser."""
  parser.add_argument(
      '--hot-tier-size',
      type=arg_parsers.BinarySize(
          default_unit='GiB',
          suggested_binary_size_scales=['GiB'],
          type_abbr='B',
      ),
      help="""The hot tier size of the Storage Pool in GiB units.
              This is a required field when --allow-auto-tiering is set for flex service level.""",
  )


def AddStoragePoolEnableHotTierAutoResizeArg(parser):
  """Adds the Enable Hot Tier Auto Resize arg to the arg parser."""
  parser.add_argument(
      '--enable-hot-tier-auto-resize',
      type=arg_parsers.ArgBoolean(
          truthy_strings=netapp_util.truthy, falsey_strings=netapp_util.falsey
      ),
      help="""Boolean flag indicating whether Storage Pool is allowed to use hot tier auto resize""",
  )


def AddStoragePoolUnifiedPoolArg(parser):
  """Adds the Unified Pool arg to the  parser."""
  parser.add_argument(
      '--unified-pool',
      type=arg_parsers.ArgBoolean(
          truthy_strings=netapp_util.truthy, falsey_strings=netapp_util.falsey
      ),
      help="""Boolean flag indicating whether Storage Pool is a unified pool that supports BLOCK storage. Defaults to False if not specified.""",
      hidden=True,
  )


def AddStoragePoolQosTypeArg(parser, messages):
  GetStoragePoolQosTypeArg(
      messages
  ).choice_arg.AddToParser(parser)

## Helper functions to combine Storage Pools args / flags for gcloud commands ##


def AddStoragePoolCreateArgs(parser, release_track):
  """Add args for creating a Storage Pool."""
  concept_parsers.ConceptParser([
      flags.GetStoragePoolPresentationSpec('The Storage Pool to create.')
  ]).AddToParser(parser)
  flags.AddResourceDescriptionArg(parser, 'Storage Pool')
  flags.AddResourceCapacityArg(parser, 'Storage Pool')
  flags.AddResourceAsyncFlag(parser)
  labels_util.AddCreateLabelsFlags(parser)
  messages = netapp_api_util.GetMessagesModule(release_track=release_track)
  AddStoragePoolServiceLevelArg(
      parser, messages=messages, required=True
  )
  AddStoragePoolNetworkArg(parser)
  AddStoragePoolActiveDirectoryArg(parser)
  AddStoragePoolKmsConfigArg(parser)
  AddStoragePoolEnableLdapArg(parser)
  AddStoragePoolZoneArg(parser)
  AddStoragePoolReplicaZoneArg(parser)
  AddStoragePoolAllowAutoTieringArg(parser)
  AddStoragePoolCustomPerformanceEnabledArg(parser)
  AddStoragePoolTotalThroughputArg(parser)
  AddStoragePoolTotalIopsArg(parser)
  AddStoragePoolQosTypeArg(parser, messages)
  if (release_track == base.ReleaseTrack.ALPHA or
      release_track == base.ReleaseTrack.BETA):
    AddStoragePoolHotTierSizeArg(parser)
    AddStoragePoolEnableHotTierAutoResizeArg(parser)
    AddStoragePoolUnifiedPoolArg(parser)
    AddStoragePoolTypeArg(parser, messages)


def AddStoragePoolDeleteArgs(parser):
  """Add args for deleting a Storage Pool."""
  concept_parsers.ConceptParser([
      flags.GetStoragePoolPresentationSpec('The Storage Pool to delete.')
  ]).AddToParser(parser)
  flags.AddResourceAsyncFlag(parser)


def AddStoragePoolUpdateArgs(parser, release_track):
  """Add args for updating a Storage Pool."""
  messages = netapp_api_util.GetMessagesModule(release_track=release_track)
  concept_parsers.ConceptParser([
      flags.GetStoragePoolPresentationSpec('The Storage Pool to update.')
  ]).AddToParser(parser)
  flags.AddResourceDescriptionArg(parser, 'Storage Pool')
  flags.AddResourceAsyncFlag(parser)
  flags.AddResourceCapacityArg(parser, 'Storage Pool', required=False)
  labels_util.AddUpdateLabelsFlags(parser)
  AddStoragePoolActiveDirectoryArg(parser)
  AddStoragePoolZoneArg(parser)
  AddStoragePoolReplicaZoneArg(parser)
  AddStoragePoolAllowAutoTieringArg(parser)
  AddStoragePoolTotalThroughputArg(parser)
  AddStoragePoolQosTypeArg(parser, messages)
  AddStoragePoolTotalIopsArg(parser)
  if (release_track == base.ReleaseTrack.ALPHA or
      release_track == base.ReleaseTrack.BETA):
    AddStoragePoolHotTierSizeArg(parser)
    AddStoragePoolEnableHotTierAutoResizeArg(parser)


def AddStoragePoolSwitchArg(parser):
  """Add args for switching zones of a Storage Pool."""
  concept_parsers.ConceptParser([
      flags.GetStoragePoolPresentationSpec('The Storage Pool to switch.')
  ]).AddToParser(parser)
  flags.AddResourceAsyncFlag(parser)


def AddStoragePoolValidateDirectoryServiceArg(parser):
  """Add args for validating directory service of a Storage Pool."""
  concept_parsers.ConceptParser([
      flags.GetStoragePoolPresentationSpec('The Storage Pool to validate.')
  ]).AddToParser(parser)
  flags.AddResourceAsyncFlag(parser)
  AddStoragePoolDirectoryServiceTypeArg(parser)
