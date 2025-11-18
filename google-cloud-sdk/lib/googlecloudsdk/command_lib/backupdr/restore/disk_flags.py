# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Flags for backup-dr restore disk commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.backupdr import util
from googlecloudsdk.command_lib.util.apis import arg_utils


def AddNameArg(parser, required=True):
  parser.add_argument(
      '--name',
      type=str,
      required=required,
      help='Name of the restored Disk.',
  )


def AddTargetZoneArg(parser, required=False):
  parser.add_argument(
      '--target-zone',
      type=str,
      required=required,
      help=(
          'Zone where the target disk is restored. This flag is mutually'
          ' exclusive with --target-region.'
      ),
  )


def AddTargetRegionArg(parser, required=False):
  parser.add_argument(
      '--target-region',
      type=str,
      required=required,
      help=(
          'Region where the target disk is restored. This flag is mutually'
          ' exclusive with --target-zone.'
      ),
  )


def AddTargetProjectArg(parser, required=True):
  parser.add_argument(
      '--target-project',
      type=str,
      required=required,
      help='Project where the restore should happen.',
  )


def AddReplicaZonesArg(parser, required=True):
  parser.add_argument(
      '--replica-zones',
      type=arg_parsers.ArgList(min_length=2, max_length=2, element_type=str),
      metavar='ZONE',
      required=required,
      help=(
          'A comma-separated list of exactly 2 URLs of the zones where the disk'
          ' should be replicated to. Required when restoring'
          ' to a regional disk. The zones must be in the same region as'
          ' specified in the --target-region flag. See available zones with'
          ' gcloud compute zones list.'
      ),
  )


def AddLicensesArg(parser, required=False):
  parser.add_argument(
      '--licenses',
      type=arg_parsers.ArgList(min_length=1),
      metavar='LICENSE',
      required=required,
      help=(
          'A list of URIs to license resources. The provided licenses will be'
          ' added onto the created disks to indicate the licensing and billing'
          ' policies.'
      ),
  )


def AddGuestOsFeaturesArgs(parser, required=False):
  """Adds a --guest-os-features flag to the given parser.

  Args:
    parser: A given parser.
    required: Whether the argument is required or not.
  """
  guest_os_features_options = (
      'VIRTIO_SCSI_MULTIQUEUE',
      'WINDOWS',
      'MULTI_IP_SUBNET',
      'UEFI_COMPATIBLE',
      'SEV_CAPABLE',
      'SEV_LIVE_MIGRATABLE',
      'SEV_LIVE_MIGRATABLE_V2',
      'SEV_SNP_CAPABLE',
      'GVNIC',
      'IDPF',
      'TDX_CAPABLE',
      'SUSPEND_RESUME_COMPATIBLE',
  )
  guest_os_features_validator = util.GetOneOfValidator(
      'guest-os-features', guest_os_features_options
  )
  parser.add_argument(
      '--guest-os-features',
      type=arg_parsers.ArgList(guest_os_features_validator),
      metavar='GUEST_OS_FEATURES',
      required=required,
      help=(
          'Enables one or more features for VM instances that use the image'
          ' for their boot disks. See the descriptions of supported features'
          ' at: https://cloud.google.com/compute/docs/images/'
          'create-delete-deprecate-private-images#guest-os-features.'
          ' GUEST_OS_FEATURE must be one of: {}.'.format(
              ', '.join(guest_os_features_options)
          )
      ),
  )


def AddDescriptionArg(parser, required=False):
  """Description of the restored disk."""
  parser.add_argument(
      '--description',
      type=str,
      required=required,
      help='Specifies a textual description of the restored disk.',
  )


def AddTypeArg(parser, required=True):
  """Adds a --type flag to the given parser.

  Args:
    parser: A given parser.
    required: Whether the argument is required or not.
  """
  help_text = """\
URL of the disk type describing which disk type to use to restore the disk. For example: projects/project/zones/zone/diskTypes/pd-ssd. To get a list of available disk types, run gcloud compute disk-types list. The default disk type is pd-standard.
"""
  parser.add_argument(
      '--type',
      help=help_text,
      type=str,
      required=required,
  )


def AddAccessModeArg(parser, required=True):
  parser.add_argument(
      '--access-mode',
      choices={
          'READ_WRITE_SINGLE': (
              'The default AccessMode, means the disk can be attached to single'
              ' instance in RW mode.'
          ),
          'READ_ONLY_MANY': (
              'The AccessMode means the disk can be attached to multiple'
              ' instances in RW mode.'
          ),
          'READ_WRITE_MANY': (
              'The AccessMode means the disk can be attached to multiple'
              ' instances in RO mode.'
          ),
      },
      type=arg_utils.ChoiceToEnumName,
      required=required,
      help=(
          'Specifies how VMs attached to the disk can access the data on the'
          ' disk. To grant read-only access to multiple VMs attached to the'
          ' disk, set access-mode to READ_ONLY_MANY. To grant read-write access'
          ' to only one VM attached to the disk, use READ_WRITE_SINGLE.'
          ' READ_WRITE_SINGLE is used if omitted. ACCESS_MODE must be one of:'
          ' READ_ONLY_MANY, READ_WRITE_MANY, READ_WRITE_SINGLE.'
      ),
  )


def AddLabelsArg(parser, required=False):
  """Labels to be added to the disk."""
  helptext = """\
      List of label KEY=VALUE pairs to add.

      Keys must start with a lowercase character and contain only hyphens (-),
      underscores (_), lowercase characters, and numbers. Values must contain
      only hyphens (-), underscores (_), lowercase characters, and numbers.
      """
  parser.add_argument(
      '--labels',
      required=required,
      type=arg_parsers.ArgDict(),
      default={},
      metavar='KEY=VALUE',
      help=helptext,
  )


def AddProvisionedIopsArg(parser, required=True):
  """Machine type used for the restored disk."""
  parser.add_argument(
      '--provisioned-iops',
      type=arg_parsers.BoundedInt(),
      required=required,
      help=(
          'Provisioned IOPS of disk to create. Only for use with disks of type '
          'pd-extreme and hyperdisk-extreme.'
      ),
  )


def AddArchitectureArg(parser, required=False):
  return parser.add_argument(
      '--architecture',
      choices={
          'X86_64': 'The disk can only be used with x86_64 machines.',
          'ARM64': 'The disk can only be used with ARM64 machines.',
      },
      type=arg_utils.ChoiceToEnumName,
      required=required,
      help=(
          'Specifies the architecture or processor type that this disk can'
          ' support. For available processor types on Compute Engine, see'
          ' https://cloud.google.com/compute/docs/cpu-platforms. ARCHITECTURE'
          ' must be one of: ARM64, X86_64'
      ),
  )


def AddConfidentialComputeArg(parser, required=False):
  return parser.add_argument(
      '--confidential-compute',
      required=required,
      action='store_true',
      help="""
      Creates the disk with confidential compute mode enabled. Encryption with a Cloud KMS key is required to enable this option.
      """,
  )


def AddSizeArg(parser, required=False):
  """Size of the disk."""
  helptext = """\
      Size of the disk in GB.
      Disk size must be a multiple of 1 GB. If disk size is not specified,
      the default size of 500GB for pd-standard disks, 100GB for
      pd-balanced disks, 100GB for pd-ssd disks, and 1000GB for pd-extreme disks
      will be used.
      For details about disk size limits,
      refer to: https://cloud.google.com/compute/docs/disks
      """
  parser.add_argument(
      '--size',
      type=arg_parsers.BoundedInt(),
      required=required,
      help=helptext,
  )


def AddProvisionedThroughputArg(parser, required=False):
  parser.add_argument(
      '--provisioned-throughput',
      type=arg_parsers.BoundedInt(),
      required=required,
      help=(
          'Provisioned throughput of disk to create. The throughput unit is  '
          'MB per sec.  Only for use with disks of type hyperdisk-throughput.'
      ),
  )


def AddResourcePoliciesArg(parser, required=False):
  """ResourcePolicies to be added to the disk."""
  helptext = """\
      A list of resource policy names to be added to the disk.
      The policies must exist in the same region as the disk.
      """
  parser.add_argument(
      '--resource-policies',
      type=arg_parsers.ArgList(min_length=1),
      metavar='RESOURCE_POLICY',
      required=required,
      help=helptext,
  )


def AddKmsKeyArg(parser, required=False):
  """Kms key to be added to the instance."""
  helptext = """\
      The Cloud KMS (Key Management Service) cryptokey that will be used to protect the disk
      Provide the full resource name of the cryptokey in the format:
      projects/<project>/locations/<location>/keyRings/<key-ring>/cryptoKeys/<key>
      """
  parser.add_argument(
      '--kms-key',
      type=str,
      required=required,
      help=helptext,
  )


def AddClearEncryptionKeyArg(parser):
  """Clear encryption key override for the disk."""
  helptext = """\
      The restored disk reverts to GMEK (CMEK is disabled).
      """
  parser.add_argument(
      '--clear-encryption-key',
      action='store_true',
      required=False,
      help=helptext,
  )


def AddStoragePoolArg(parser, required=False):
  helptext = """
      Specifies the URI of the storage pool in which the disk is created.
    """
  parser.add_argument(
      '--storage-pool',
      type=str,
      required=required,
      help=helptext,
  )
