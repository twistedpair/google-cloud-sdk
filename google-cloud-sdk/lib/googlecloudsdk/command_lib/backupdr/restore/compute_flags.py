# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Flags for backup-dr restore compute commands."""

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
      help='Name of the restored Compute Instance.',
  )


def AddTargetZoneArg(parser, required=True):
  parser.add_argument(
      '--target-zone',
      type=str,
      required=required,
      help='Zone where the target instance is restored.',
  )


def AddTargetProjectArg(parser, required=True):
  parser.add_argument(
      '--target-project',
      type=str,
      required=required,
      help='Project where the restore should happen.',
  )


def AddNetworkInterfaceArg(parser, required=True):
  """Network interface of the restored resource."""
  network_tier_options = ('NETWORK_TIER_UNSPECIFIED', 'STANDARD', 'PREMIUM')
  stack_type_options = ('STACK_TYPE_UNSPECIFIED', 'IPV4_ONLY', 'IPV4_IPV6')
  nic_type_options = ('NIC_TYPE_UNSPECIFIED', 'VIRTIO_NET', 'GVNIC')

  network_tier_validator = util.GetOneOfValidator(
      'network-tier', network_tier_options
  )
  stack_type_validator = util.GetOneOfValidator(
      'stack-type', stack_type_options
  )
  nic_type_validator = util.GetOneOfValidator('nic-type', nic_type_options)
  network_interface_spec = {
      'network': str,
      'subnet': str,
      'private-network-ip': str,
      'internal-ipv6-address': str,
      'internal-ipv6-prefix-length': int,
      'address': str,
      'external-ipv6-address': str,
      'external-ipv6-prefix-length': int,
      'public-ptr-domain': str,
      'ipv6-public-ptr-domain': str,
      'network-tier': network_tier_validator,
      'aliases': str,
      'stack-type': stack_type_validator,
      'queue-count': int,
      'nic-type': nic_type_validator,
      'network-attachment': str,
  }
  parser.add_argument(
      '--network-interface',
      required=required,
      type=arg_parsers.ArgDict(spec=network_interface_spec),
      action='append',
      metavar='PROPERTY=VALUE',
      help=(
          'Adds a network interface to the instance. This flag can be repeated'
          ' to specify multiple network interfaces. The following keys are'
          ' allowed: network, subnet, private-network-ip,'
          ' internal-ipv6-address, internal-ipv6-prefix-length, address,'
          ' external-ipv6-address, external-ipv6-prefix-length,'
          ' public-ptr-domain, ipv6-public-ptr-domain, network-tier, aliases,'
          ' stack-type, queue-count, nic-type, network-attachment'
      ),
  )


def AddServiceAccountArg(parser, required=True):
  """Service account used to restore."""
  parser.add_argument(
      '--service-account',
      type=str,
      required=required,
      help=(
          'A service account is an identity attached to the instance. Its'
          ' access tokens can be accessed through the instance metadata server'
          ' and are used to authenticate applications on the instance. The'
          ' account can be set using an email address corresponding to the'
          ' required service account. If not provided, the instance will use'
          " the project's default service account."
      ),
  )


def AddScopesArg(parser, required=True):
  """Scopes for the service account used to restore."""
  scopes_group = parser.add_mutually_exclusive_group()

  scopes_group.add_argument(
      '--scopes',
      type=arg_parsers.ArgList(str),
      required=required,
      metavar='SCOPE',
      help=(
          'If not provided, the instance will be assigned the default scopes,'
          ' described below. However, if neither --scopes nor --no-scopes are'
          ' specified and the project has no default service account, then the'
          ' instance will be created with no scopes. Note that the level of'
          ' access that a service account has is determined by a combination of'
          ' access scopes and IAM roles so you must configure both access'
          ' scopes and IAM roles for the service account to work properly.'
          ' SCOPE can be either the full URI of the scope or an alias. Default'
          ' scopes are assigned to all instances. Available aliases are:'
          ' https://cloud.google.com/sdk/gcloud/reference/compute/instances/create#--scopes'
      ),
  )

  scopes_group.add_argument(
      '--no-scopes',
      action='store_true',
      help='Create the instance with no scopes.',
  )


def AddCreateDiskArg(parser, required=True):
  """Attaches persistent disks to the instances."""

  disk_spec = {
      'name': str,
      'replica-zones': arg_parsers.ArgList(str, custom_delim_char=' '),
      'device-name': str,
  }
  parser.add_argument(
      '--create-disk',
      required=required,
      type=arg_parsers.ArgDict(spec=disk_spec),
      action='append',
      metavar='PROPERTY=VALUE',
      help="""
          Creates and attaches persistent disks to the instances.

          *name*: Specifies the name of the disk.

          *replica-zones*: Required for each regional disk associated with the
          instance. Specify the URLs of the zones where the disk should be
          replicated to. You must provide exactly two replica zones, and one
          zone must be the same as the instance zone.

          *device-name*: Device name of the disk from the source instance.
          """,
  )


def AddDescriptionArg(parser, required=True):
  """Description of the restored instance."""
  parser.add_argument(
      '--description',
      type=str,
      required=required,
      help='Specifies a textual description of the restored instance.',
  )


def AddMetadataArg(parser, required=True):
  """Metadata to be made available to the guest operating system."""
  helptext = """\
      Metadata to be made available to the guest operating system
      running on the instances. Each metadata entry is a key/value
      pair separated by an equals sign. Each metadata key must be unique
      and have a max of 128 bytes in length. Each value must have a max of
      256 KB in length. Multiple arguments can be
      passed to this flag, e.g.,
      ``--metadata key-1=value-1,key-2=value-2,key-3=value-3''.
      The combined total size for all metadata entries is 512 KB.

      In images that have Compute Engine tools installed on them,
      such as the
      link:https://cloud.google.com/compute/docs/images[official images],
      the following metadata keys have special meanings:

      *startup-script*::: Specifies a script that will be executed
      by the instances once they start running. For convenience,
      ``--metadata-from-file'' can be used to pull the value from a
      file.

      *startup-script-url*::: Same as ``startup-script'' except that
      the script contents are pulled from a publicly-accessible
      location on the web.


      For startup scripts on Windows instances, the following metadata keys
      have special meanings:
      ``windows-startup-script-url'',
      ``windows-startup-script-cmd'', ``windows-startup-script-bat'',
      ``windows-startup-script-ps1'', ``sysprep-specialize-script-url'',
      ``sysprep-specialize-script-cmd'', ``sysprep-specialize-script-bat'',
      and ``sysprep-specialize-script-ps1''. For more information, see
      [Running startup scripts](https://cloud.google.com/compute/docs/startupscript).
      """
  parser.add_argument(
      '--metadata',
      required=required,
      type=arg_parsers.ArgDict(min_length=1),
      default={},
      metavar='KEY=VALUE',
      help=helptext,
      action=arg_parsers.StoreOnceAction,
  )


def AddLabelsArg(parser, required=True):
  """Labels to be added to the instance."""
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


def AddTagsArg(parser, required=True):
  """Tags to be added to the instance."""
  helptext = """\
      Specifies a list of tags to apply to the instance. These tags allow
      network firewall rules and routes to be applied to specified VM instances.
      See gcloud_compute_firewall-rules_create(1) for more details.
      """
  parser.add_argument(
      '--tags',
      required=required,
      type=arg_parsers.ArgList(min_length=1),
      metavar='TAG',
      help=helptext,
  )


def AddMachineTypeArg(parser, required=True):
  """Machine type used for the restored instance."""
  helptext = """\
      Specifies the machine type used for the restored instance. To get a list
      of available machine types, run 'gcloud compute machine-types list'. If
      unspecified, the default type will be based on the source instance.

      This can either be the fully qualified path or the name.
      For example:
      * ``--machine-type=projects/my-project/zones/us-central1-a/machineTypes/n1-standard-1''
      * ``--machine-type=n1-standard-1''
      """
  parser.add_argument(
      '--machine-type',
      type=str,
      required=required,
      help=helptext,
  )


def AddHostnameArg(parser, required=True):
  """Hostname of the restore instance."""
  helptext = """\
      Specify the hostname of the restore instance to be created. The specified
      hostname must be RFC1035 compliant. If hostname is not specified, the
      default hostname is [INSTANCE_NAME].c.[TARGET_PROJECT_ID].internal when using the
      global DNS, and [INSTANCE_NAME].[ZONE].c.[TARGET_PROJECT_ID].internal when using
      zonal DNS.
      """
  parser.add_argument(
      '--hostname',
      type=str,
      required=required,
      help=helptext,
  )


def AddEnableUefiNetworkingArg(parser, required=True):
  """Enable UEFI networking for the instance creation."""
  helptext = """\
      If set to true, enables UEFI networking for the instance creation.
      """
  parser.add_argument(
      '--enable-uefi-networking',
      action=arg_parsers.StoreTrueFalseAction,
      required=required,
      help=helptext,
  )


def AddThreadsPerCoreArg(parser, required=True):
  """The number of visible threads per physical core."""
  helptext = """
      The number of visible threads per physical core. To disable simultaneous
      multithreading (SMT) set this to 1. Valid values are: 1 or 2.

      For more information about configuring SMT, see:
      https://cloud.google.com/compute/docs/instances/configuring-simultaneous-multithreading.
    """
  parser.add_argument(
      '--threads-per-core',
      type=int,
      required=required,
      help=helptext,
  )


def AddVisibleCoreCountArg(parser, required=True):
  """The number of physical cores to expose to the instance's guest operating system."""
  helptext = """
      The number of physical cores to expose to the instance's guest operating
      system. The number of virtual CPUs visible to the instance's guest
      operating system is this number of cores multiplied by the instance's
      count of visible threads per physical core.
    """
  parser.add_argument(
      '--visible-core-count',
      type=int,
      required=required,
      help=helptext,
  )


def AddAcceleratorArg(parser, required=True):
  """Attaches accelerators (e.g. GPUs) to the instances."""
  helptext = """\
      Attaches accelerators (e.g. GPUs) to the instances.

      *type*::: The specific type (e.g. nvidia-tesla-k80 for nVidia Tesla K80)
      of accelerator to attach to the instances. Use 'gcloud compute
      accelerator-types list' to learn about all available accelerator types.

      *count*::: Number of accelerators to attach to each
      instance. The default value is 1.
      """
  parser.add_argument(
      '--accelerator',
      type=arg_parsers.ArgDict(
          spec={'type': str, 'count': int}, required_keys=['type']
      ),
      required=required,
      help=helptext,
  )


def AddMinCpuPlatform(parser, required=True):
  """Minimum CPU platform to be used for the instance."""
  helptext = """\
      When specified, the VM will be scheduled on host with specified CPU
      architecture or a newer one. To list available CPU platforms in given
      zone, run:

          $ gcloud compute zones describe ZONE --format="value(availableCpuPlatforms)"

      Default setting is "AUTOMATIC".

      CPU platform selection is available only in selected zones.

      You can find more information on-line:
      [](https://cloud.google.com/compute/docs/instances/specify-min-cpu-platform)
      """
  parser.add_argument(
      '--min-cpu-platform',
      type=str,
      required=required,
      metavar='PLATFORM',
      help=helptext,
  )


def AddMaintenancePolicyArg(parser, required=True):
  """Maintenance policy to be used for the instance."""
  helptext = """\
      Specifies the behavior of the VMs when their host machines undergo
      maintenance. The default is MIGRATE.
      For more information, see
      https://cloud.google.com/compute/docs/instances/host-maintenance-options.
      """
  parser.add_argument(
      '--maintenance-policy',
      choices={
          'MIGRATE': (
              'The instances should be migrated to a new host. This will'
              ' temporarily impact the performance of instances during a'
              ' migration event.'
          ),
          'TERMINATE': 'The instances should be terminated.',
      },
      type=arg_utils.ChoiceToEnumName,
      required=required,
      help=helptext,
  )


def AddPreemptibleArg(parser, required=True):
  """Preemptible state to be used for the instance."""
  helptext = """\
      If provided, instances will be preemptible and time-limited. Instances
      might be preempted to free up resources for standard VM instances,
      and will only be able to run for a limited amount of time. Preemptible
      instances can not be restarted and will not migrate.
      """
  parser.add_argument(
      '--preemptible',
      action='store_true',
      default=False,
      required=required,
      help=helptext,
  )


def AddRestartOnFailureArg(parser, required=True):
  """Restart on failure state to be used for the instance."""
  helptext = """\
      The instances will be restarted if they are terminated by Compute Engine.
      This does not affect terminations performed by the user.
      """
  parser.add_argument(
      '--restart-on-failure',
      action='store_true',
      default=False,
      required=required,
      help=helptext,
  )


def AddMinNodeCpuArg(parser, required=False):
  """Minimum Node CPUs to be used for the instance."""
  helptext = """\
      Minimum number of virtual CPUs this instance will consume when running on
      a sole-tenant node.
      """
  parser.add_argument(
      '--min-node-cpu',
      type=int,
      required=required,
      help=helptext,
  )


def AddProvisioningModelArg(parser, required=False):
  """Provisioning model to be used for the instance."""
  helptext = """\
      Specifies provisioning model, which determines price, obtainability,
      and runtime for the restored VM instance.
      """
  parser.add_argument(
      '--provisioning-model',
      choices={
          'SPOT': (
              'Spot VMs are spare capacity; Spot VMs are discounted '
              'to have much lower prices than standard VMs '
              'but have no guaranteed runtime. Spot VMs are the new version '
              'of preemptible VM instances, except Spot VMs do not have '
              'a 24-hour maximum runtime.'
          ),
          'STANDARD': (
              'Default. Standard provisioning model for VM instances, '
              'which has user-controlled runtime '
              'but no Spot discounts.'
          ),
      },
      type=arg_utils.ChoiceToEnumName,
      required=required,
      help=helptext,
  )


def AddInstanceTerminationActionArg(parser, required=False):
  """Termination action to be used for the instance."""
  helptext = """\
      Specifies the termination action that will be taken upon VM preemption
        (--provisioning-model=SPOT) or automatic instance
        termination (--max-run-duration or --termination-time).
      """
  parser.add_argument(
      '--instance-termination-action',
      choices={
          'STOP': (
              'Default only for Spot VMs. Stop the VM without preserving'
              ' memory. The VM can be restarted later.'
          ),
          'DELETE': 'Permanently delete the VM.',
      },
      type=arg_utils.ChoiceToEnumName,
      required=required,
      help=helptext,
  )


def AddLocalSsdRecoveryTimeoutArg(parser, required=False):
  """Local SSD recovery timeout to be used for the instance."""
  helptext = """\
      Specifies the maximum amount of time a Local SSD VM should wait while
      recovery of the Local SSD state is attempted. Its value should be in
      between 0 and 168 hours with hour granularity and the default value being 1
      hour.
      """
  parser.add_argument(
      '--local-ssd-recovery-timeout',
      type=arg_parsers.Duration(
          default_unit='h', lower_bound='0h', upper_bound='168h'
      ),
      required=required,
      help=helptext,
  )


def AddNodeAffinityFileArg(parser, required=False):
  """Node affinity file to be used for the instance."""
  helptext = """\
      The JSON/YAML file containing the configuration of desired nodes onto
      which this instance could be scheduled. These rules filter the nodes
      according to their node affinity labels. A node's affinity labels come
      from the node template of the group the node is in.

      The file should contain a list of a JSON/YAML objects. For an example,
      see https://cloud.google.com/compute/docs/nodes/provisioning-sole-tenant-vms#configure_node_affinity_labels.
      The following list describes the fields:

      *key*::: Corresponds to the node affinity label keys of
      the Node resource.
      *operator*::: Specifies the node selection type. Must be one of:
        `IN`: Requires Compute Engine to seek for matched nodes.
        `NOT_IN`: Requires Compute Engine to avoid certain nodes.
      *values*::: Optional. A list of values which correspond to the node
      affinity label values of the Node resource.
      """
  parser.add_argument(
      '--node-affinity-file',
      type=arg_parsers.YAMLFileContents(),
      required=required,
      help=helptext,
  )


def AddReservationArgs(parser, required=False):
  """Reservation affinity to be used for the instance."""
  reservation_group_helptext = """Specifies the reservation for the instance."""
  reservation_affinity_helptext = """\
      Specifies the reservation affinity of the instance.
      """
  reservation_help_text = """The name of the reservation, required when `--reservation-affinity=specific`."""

  group = parser.add_group(help=reservation_group_helptext)

  group.add_argument(
      '--reservation-affinity',
      choices={
          'any': 'Consume any available, matching reservation.',
          'none': 'Do not consume from any reserved capacity.',
          'specific': 'Must consume from a specific reservation.',
      },
      required=required,
      help=reservation_affinity_helptext,
  )

  group.add_argument(
      '--reservation',
      required=required,
      help=reservation_help_text,
  )


def AddEnableDisplayDeviceArg(parser, required=False):
  """Enable display device for the instance."""
  helptext = """\
      Enable a display device on the restored VM instances. Disabled by default.
      """
  parser.add_argument(
      '--enable-display-device',
      action='store_true',
      required=required,
      help=helptext,
  )


def AddCanIpForwardArg(parser, required=False):
  """Enable can ip forward for the restored instance."""
  helptext = """\
      If provided, allows the restored instances to send and receive packets
      with non-matching destination or source IP addresses.
      """
  parser.add_argument(
      '--can-ip-forward',
      action='store_true',
      required=required,
      help=helptext,
  )


def AddPrivateIpv6GoogleAccessArg(parser, required=False):
  """Enable private ipv6 google access for the  restored instance."""
  helptext = """\
      The private IPv6 Google access type for the restored VM.
      """
  enum_mappings = {
      'inherit-subnetwork': 'INHERIT_FROM_SUBNETWORK',
      'enable-bidirectional-access': 'ENABLE_BIDIRECTIONAL_ACCESS_TO_GOOGLE',
      'enable-outbound-vm-access': 'ENABLE_OUTBOUND_VM_ACCESS_TO_GOOGLE',
  }
  helptext += 'PRIVATE_IPV6_GOOGLE_ACCESS_TYPE must be one of: {}'.format(
      ', '.join(list(enum_mappings.keys()))
  )
  parser.add_argument(
      '--private-ipv6-google-access-type',
      type=util.EnumMapper(enum_mappings).Parse,
      required=required,
      help=helptext,
  )


def AddNetworkPerformanceConfigsArg(parser, required=False):
  """Enable network performance config for the restored instance."""
  helptext = """\
      Configures network performance settings for the restored instance.
      If this flag is not specified, the restored instance will be created
      with its source instance's network performance configuration.

      *total-egress-bandwidth-tier*::: Total egress bandwidth is the available
      outbound bandwidth from a VM, regardless of whether the traffic
      is going to internal IP or external IP destinations.
      The following tier values are allowed: [DEFAULT, TIER_1]
      """
  parser.add_argument(
      '--network-performance-configs',
      type=arg_parsers.ArgDict(
          spec={
              'total-egress-bandwidth-tier': str,
          },
      ),
      metavar='PROPERTY=VALUE',
      required=required,
      help=helptext,
  )


def AddConfidentialComputeArg(parser, required=False):
  """Enable confidential compute for the restored instance."""
  helptext = """\
      The restored instance boots with Confidential Computing enabled.
      Confidential Computing is based on Secure Encrypted Virtualization (SEV),
      an AMD virtualization feature for running confidential instances.
      """
  parser.add_argument(
      '--confidential-compute',
      action='store_true',
      required=required,
      help=helptext,
  )


def AddDeletionProtectionArg(parser, required=False):
  """Enable deletion protection for the restored instance."""
  helptext = """\
      Enables deletion protection for the restored instance.
      """
  parser.add_argument(
      '--deletion-protection',
      action='store_true',
      required=required,
      help=helptext,
  )


def AddResourceManagerTagsArg(parser, required=False):
  """ResourceManagerTags to be added to the instance."""
  helptext = """\
      Specifies a list of resource manager tags to apply to the instance.
      """
  parser.add_argument(
      '--resource-manager-tags',
      type=arg_parsers.ArgDict(),
      metavar='KEY=VALUE',
      required=required,
      help=helptext,
  )


def AddResourcePoliciesArg(parser, required=False):
  """ResourcePolicies to be added to the instance."""
  helptext = """\
      A list of resource policy names to be added to the instance.
      The policies must exist in the same region as the instance.
      """
  parser.add_argument(
      '--resource-policies',
      type=arg_parsers.ArgList(min_length=1),
      metavar='RESOURCE_POLICY',
      required=required,
      help=helptext,
  )


def AddKeyRevocationActionTypeArg(parser, required=False):
  """KeyRevocationActionType to be added to the instance."""
  helptext = """\
      Specifies the behavior of the instance when the KMS key of one of its
      attached disks is revoked. The default is none. POLICY must be one of:
      * none
      No operation is performed.
      * stop
      The instance is stopped when the KMS key of one of its attached disks is
      revoked.
      """
  enum_mappings = {
      'none': 'NONE',
      'stop': 'STOP',
  }
  parser.add_argument(
      '--key-revocation-action-type',
      metavar='POLICY',
      type=util.EnumMapper(enum_mappings).Parse,
      required=required,
      help=helptext,
  )


def AddInstanceKmsKeyArg(parser, required=False):
  """InstanceKmsKey to be added to the instance."""
  helptext = """\
      The Cloud KMS (Key Management Service) cryptokey that will be used to
      protect the restored instance.

      Provide the full resource name of the cryptokey in the format:
      `projects/<project>/locations/<location>/keyRings/<key-ring>/cryptoKeys/<key>`
      """
  parser.add_argument(
      '--instance-kms-key',
      type=str,
      required=required,
      help=helptext,
  )
