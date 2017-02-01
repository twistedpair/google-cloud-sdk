# Copyright 2016 Google Inc. All Rights Reserved.
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
"""Flags and helpers for the compute VM instances commands."""
import argparse

from googlecloudsdk.api_lib.compute import constants
from googlecloudsdk.api_lib.compute import containers_utils
from googlecloudsdk.api_lib.compute import image_utils
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.compute import flags as compute_flags
from googlecloudsdk.command_lib.compute import scope as compute_scope
from googlecloudsdk.core import log
import ipaddr

MIGRATION_OPTIONS = {
    'MIGRATE': (
        'The instances should be migrated to a new host. This will temporarily '
        'impact the performance of instances during a migration event.'),
    'TERMINATE': 'The instances should be terminated.',
}

LOCAL_SSD_INTERFACES = ['NVME', 'SCSI']

DISK_METAVAR = (
    'name=NAME [mode={ro,rw}] [boot={yes,no}] [device-name=DEVICE_NAME] '
    '[auto-delete={yes,no}]')

DISK_METAVAR_ZONAL_OR_REGIONAL = (
    'name=NAME [mode={ro,rw}] [boot={yes,no}] [device-name=DEVICE_NAME] '
    '[auto-delete={yes,no}] [scope={zonal,regional}]')

INSTANCE_ARG = compute_flags.ResourceArgument(
    resource_name='instance',
    completion_resource_id='compute.instances',
    zonal_collection='compute.instances',
    zone_explanation=compute_flags.ZONE_PROPERTY_EXPLANATION)

INSTANCES_ARG = compute_flags.ResourceArgument(
    resource_name='instance',
    name='names',
    completion_resource_id='compute.instances',
    zonal_collection='compute.instances',
    zone_explanation=compute_flags.ZONE_PROPERTY_EXPLANATION,
    plural=True)

SSH_INSTANCE_RESOLVER = compute_flags.ResourceResolver.FromMap(
    'instance', {compute_scope.ScopeEnum.ZONE: 'compute.instances'})


def InstanceArgumentForRoute(required=True):
  return compute_flags.ResourceArgument(
      resource_name='instance',
      name='--next-hop-instance',
      completion_resource_id='compute.instances',
      required=required,
      zonal_collection='compute.instances',
      zone_explanation=compute_flags.ZONE_PROPERTY_EXPLANATION)


def InstanceArgumentForTargetInstance(required=True):
  return compute_flags.ResourceArgument(
      resource_name='instance',
      name='--instance',
      completion_resource_id='compute.instances',
      required=required,
      zonal_collection='compute.instances',
      short_help=('The name of the virtual machine instance that will handle '
                  'the traffic.'),
      zone_explanation=(
          'If not specified, it will be set to the same as zone.'))


def InstanceArgumentForTargetPool(action, required=True):
  return compute_flags.ResourceArgument(
      resource_name='instances',
      name='--instances',
      completion_resource_id='compute.instances',
      required=required,
      zonal_collection='compute.instances',
      short_help=(
          'Specifies a list of instances to {0} the target pool.'.format(action)
      ),
      plural=True,
      zone_explanation=compute_flags.ZONE_PROPERTY_EXPLANATION)


def AddImageArgs(parser):
  """Adds arguments related to images for instances and instance-templates."""

  def AddImageHelp():
    """Returns the detailed help for the `--image` flag."""
    return """
          Specifies the boot image for the instances. For each
          instance, a new boot disk will be created from the given
          image. Each boot disk will have the same name as the
          instance. To view a list of public images and projects, run
          `$ gcloud compute images list`.

          When using this option, ``--boot-disk-device-name'' and
          ``--boot-disk-size'' can be used to override the boot disk's
          device name and size, respectively.
          """

  image_group = parser.add_mutually_exclusive_group()
  image = image_group.add_argument(
      '--image',
      help='The image that the boot disk will be initialized with.',
      metavar='IMAGE')
  image.detailed_help = AddImageHelp
  image_utils.AddImageProjectFlag(parser)

  image_group.add_argument(
      '--image-family',
      help=("""\
          The family of the image that the boot disk will be initialized
          with. When a family is specified instead of an image, the latest
          non-deprecated image associated with that family is used.

          By default, ``{default_image_family}'' is assumed for this flag.
          """.format(
              default_image_family=constants.DEFAULT_IMAGE_FAMILY)))


def AddCanIpForwardArgs(parser):
  parser.add_argument(
      '--can-ip-forward',
      action='store_true',
      help=('If provided, allows the instances to send and receive packets '
            'with non-matching destination or source IP addresses.'))


def AddLocalSsdArgs(parser):
  """Adds local SSD argument for instances and instance-templates."""

  local_ssd = parser.add_argument(
      '--local-ssd',
      type=arg_parsers.ArgDict(spec={
          'device-name': str,
          'interface': (lambda x: x.upper()),
      }),
      action='append',
      help='(BETA) Specifies instances with attached local SSDs.')
  local_ssd.detailed_help = """
      Attaches a local SSD to the instances.

      This flag is currently in BETA and may change without notice.

      *device-name*::: Optional. A name that indicates the disk name
      the guest operating system will see.  If omitted, a device name
      of the form ``local-ssd-N'' will be used.

      *interface*::: Optional. The kind of disk interface exposed to the VM
      for this SSD.  Valid values are ``SCSI'' and ``NVME''.  SCSI is
      the default and is supported by more guest operating systems.  NVME
      may provide higher performance.
      """


def AddDiskArgs(parser, enable_regional_disks=False):
  """Adds arguments related to disks for instances and instance-templates."""

  boot_disk_device_name = parser.add_argument(
      '--boot-disk-device-name',
      help='The name the guest operating system will see the boot disk as.')
  boot_disk_device_name.detailed_help = """\
      The name the guest operating system will see for the boot disk as.  This
      option can only be specified if a new boot disk is being created (as
      opposed to mounting an existing persistent disk).
      """
  boot_disk_size = parser.add_argument(
      '--boot-disk-size',
      type=arg_parsers.BinarySize(lower_bound='10GB'),
      help='The size of the boot disk.')
  boot_disk_size.detailed_help = """\
      The size of the boot disk. This option can only be specified if a new
      boot disk is being created (as opposed to mounting an existing
      persistent disk). The value must be a whole number followed by a size
      unit of ``KB'' for kilobyte, ``MB'' for megabyte, ``GB'' for gigabyte,
      or ``TB'' for terabyte. For example, ``10GB'' will produce a 10 gigabyte
      disk. The minimum size a boot disk can have is 10 GB. Disk size must be a
      multiple of 1 GB.
      """

  boot_disk_type = parser.add_argument(
      '--boot-disk-type',
      help='The type of the boot disk.')
  boot_disk_type.detailed_help = """\
      The type of the boot disk. This option can only be specified if a new boot
      disk is being created (as opposed to mounting an existing persistent
      disk). To get a list of available disk types, run
      `$ gcloud compute disk-types list`.
      """

  parser.add_argument(
      '--boot-disk-auto-delete',
      action='store_true',
      default=True,
      help='Automatically delete boot disks when their instances are deleted.')

  disk_arg_spec = {
      'name': str,
      'mode': str,
      'boot': str,
      'device-name': str,
      'auto-delete': str,
  }

  if enable_regional_disks:
    disk_arg_spec['scope'] = str

  disk = parser.add_argument(
      '--disk',
      type=arg_parsers.ArgDict(spec=disk_arg_spec),
      action='append',
      help='Attaches persistent disks to the instances.')

  detailed_help = """
      Attaches persistent disks to the instances. The disks
      specified must already exist.

      *name*::: The disk to attach to the instances. When creating
      more than one instance and using this property, the only valid
      mode for attaching the disk is read-only (see *mode* below).

      *mode*::: Specifies the mode of the disk. Supported options
      are ``ro'' for read-only and ``rw'' for read-write. If
      omitted, ``rw'' is used as a default. It is an error for mode
      to be ``rw'' when creating more than one instance because
      read-write disks can only be attached to a single instance.

      *boot*::: If ``yes'', indicates that this is a boot disk. The
      virtual machines will use the first partition of the disk for
      their root file systems. The default value for this is ``no''.

      *device-name*::: An optional name that indicates the disk name
      the guest operating system will see. If omitted, a device name
      of the form ``persistent-disk-N'' will be used.

      *auto-delete*::: If ``yes'',  this persistent disk will be
      automatically deleted when the instance is deleted. However,
      if the disk is later detached from the instance, this option
      won't apply. The default value for this is ``no''.
      """
  if enable_regional_disks:
    detailed_help += """
      *scope*::: Can be `zonal` or `regional`. If ``zonal'', the disk is
      interpreted as a zonal disk in the same zone as the instance (default).
      If ``regional'', the disk is interpreted as a regional disk in the same
      region as the instance. The default value for this is ``zonal''.

      """
  disk.detailed_help = detailed_help


def AddCreateDiskArgs(parser):
  """Adds create-disk argument for instances and instance-templates."""

  create_disk = parser.add_argument(
      '--create-disk',
      type=arg_parsers.ArgDict(spec={
          'name': str,
          'mode': str,
          'image': str,
          'image-family': str,
          'image-project': str,
          'size': arg_parsers.BinarySize(lower_bound='10GB'),
          'type': str,
          'device-name': str,
          'auto-delete': str,
      }),
      action='append',
      help='Creates and attaches persistent disks to the instances.',
      metavar='PROPERTY=VALUE')
  create_disk.detailed_help = """
      Creates and attaches persistent disks to the instances.

      *name*::: Specifies the name of the disk. This option cannot be
      specified if more than one instance is being created.

      *mode*::: Specifies the mode of the disk. Supported options
      are ``ro'' for read-only and ``rw'' for read-write. If
      omitted, ``rw'' is used as a default.

      *image*::: Specifies the name of the image that the disk will be
      initialized with. A new disk will be created based on the given
      image. To view a list of public images and projects, run
      `$ gcloud compute images list`. If omitted image-family must be
      specified to identify the image.

      *image-family*::: The family of the image that the disk will be
      initialized with. When a family is specified instead of an image,
      the latest non-deprecated image associated with that family is
      used.

      *image-project*::: The project that the image or image family
      belongs to. If not specified and either an image or image family
      is provided, the project of the instance is assumed.

      *size*::: The size of the disk. The value must be a whole number
      followed by a size unit of ``KB'' for kilobyte, ``MB'' for
      megabyte, ``GB'' for gigabyte, or ``TB'' for terabyte. For
      example, ``10GB'' will produce a 10 gigabyte disk. Disk size must
      be a multiple of 1 GB. If not specified, the default image size
      will be used for the new disk.

      *type*::: The type of the disk. To get a list of available disk
      types, run $ gcloud compute disk-types list. The default disk type
      is ``pd-standard''.

      *device-name*::: An optional name that indicates the disk name
      the guest operating system will see. If omitted, a device name
      of the form ``persistent-disk-N'' will be used.

      *auto-delete*::: If ``yes'',  this persistent disk will be
      automatically deleted when the instance is deleted. However,
      if the disk is later detached from the instance, this option
      won't apply. The default value for this is ``no''.
      """


def AddCustomMachineTypeArgs(parser):
  """Adds arguments related to custom machine types for instances."""
  custom_cpu = parser.add_argument(
      '--custom-cpu',
      type=int,
      help='Number of CPUs desired in the instance for a custom machine type.')
  custom_cpu.detailed_help = """\
      A whole number value indicating how many cores are desired in the custom
      machine type. Both --custom-cpu and --custom-memory must be specified if
      a custom machine type is desired, and the --machine-type flag must be
      omitted.
      """
  custom_memory = parser.add_argument(
      '--custom-memory',
      type=arg_parsers.BinarySize(),
      help='Amount of memory desired in the instance for a custom machine type '
      '(set units, default GiB).')
  custom_memory.detailed_help = """\
      A whole number value indicating how much memory is desired in the custom
      machine type. A size unit should be provided (eg. 3072MiB or 9GiB) - if
      no units are specified, GiB is assumed. Both --custom-cpu and
      --custom-memory must be specified if a custom machine type is desired,
      and the --machine-type flag must be omitted.
      """


def AddExtendedMachineTypeArgs(parser):
  """Adds the argument enabling extended custom machine types for instances."""
  parser.add_argument(
      '--custom-extensions',
      action='store_true',
      help=('If provided, uses extended custom machine type. Both --custom-cpu'
            ' and --custom-memory must be specified if --custom-extensions is'
            ' provided.'))


def _GetAddress(compute_client, address_ref):
  """Returns the address resource corresponding to the given reference.

  Args:
    compute_client: GCE API client,
    address_ref: resource reference to reserved IP address

  Returns:
    GCE reserved IP address resource
  """
  errors = []
  messages = compute_client.messages
  compute = compute_client.apitools_client
  res = compute_client.MakeRequests(
      requests=[(compute.addresses,
                 'Get',
                 messages.ComputeAddressesGetRequest(
                     address=address_ref.Name(),
                     project=address_ref.project,
                     region=address_ref.region))],
      errors_to_collect=errors)
  if errors:
    utils.RaiseToolException(
        errors,
        error_message='Could not fetch address resource:')
  return res[0]


def ExpandAddressFlag(resources, compute_client, address, region):
  """Resolves the --address flag value.

  If the value of --address is a name, the regional address is queried.

  Args:
    resources: resources object,
    compute_client: GCE API client,
    address: The command-line flags. The flag accessed is --address,
    region: The region.

  Returns:
    If an --address is given, the resolved IP address; otherwise None.
  """
  if not address:
    return None

  # Try interpreting the address as IPv4 or IPv6.
  try:
    ipaddr.IPAddress(address)
    return address
  except ValueError:
    # ipaddr could not resolve as an IPv4 or IPv6 address.
    pass

  # Lookup the address.
  address_ref = resources.Parse(
      address,
      collection='compute.addresses',
      params={'region': region})
  res = _GetAddress(compute_client, address_ref)
  return res.address


def ValidateDiskFlags(args):
  """Validates the values of all disk-related flags."""
  ValidateDiskCommonFlags(args)
  ValidateDiskAccessModeFlags(args)
  ValidateDiskBootFlags(args)
  ValidateCreateDiskFlags(args)


def ValidateDiskCommonFlags(args):
  """Validates the values of common disk-related flags."""

  for disk in args.disk or []:
    disk_name = disk.get('name')
    if not disk_name:
      raise exceptions.ToolException(
          '[name] is missing in [--disk]. [--disk] value must be of the form '
          '[{0}].'.format(DISK_METAVAR))

    mode_value = disk.get('mode')
    if mode_value and mode_value not in ('rw', 'ro'):
      raise exceptions.ToolException(
          'Value for [mode] in [--disk] must be [rw] or [ro], not [{0}].'
          .format(mode_value))

    auto_delete_value = disk.get('auto-delete')
    if auto_delete_value and auto_delete_value not in ['yes', 'no']:
      raise exceptions.ToolException(
          'Value for [auto-delete] in [--disk] must be [yes] or [no], not '
          '[{0}].'.format(auto_delete_value))


def ValidateDiskAccessModeFlags(args):
  """Checks disks R/O and R/W access mode."""
  for disk in args.disk or []:
    disk_name = disk.get('name')
    mode_value = disk.get('mode')
    # Ensures that the user is not trying to attach a read-write
    # disk to more than one instance.
    if len(args.names) > 1 and mode_value == 'rw':
      raise exceptions.ToolException(
          'Cannot attach disk [{0}] in read-write mode to more than one '
          'instance.'.format(disk_name))


def ValidateDiskBootFlags(args):
  """Validates the values of boot disk-related flags."""
  boot_disk_specified = False
  for disk in args.disk or []:
    # If this is a boot disk and we have already seen a boot disk,
    # we need to fail because only one boot disk can be attached.
    boot_value = disk.get('boot')
    if boot_value and boot_value not in ('yes', 'no'):
      raise exceptions.ToolException(
          'Value for [boot] in [--disk] must be [yes] or [no], not [{0}].'
          .format(boot_value))

    if boot_value == 'yes':
      if boot_disk_specified:
        raise exceptions.ToolException(
            'Each instance can have exactly one boot disk. At least two '
            'boot disks were specified through [--disk].')
      else:
        boot_disk_specified = True

  if args.image and boot_disk_specified:
    raise exceptions.ToolException(
        'Each instance can have exactly one boot disk. One boot disk '
        'was specified through [--disk] and another through [--image].')

  if boot_disk_specified:
    if args.boot_disk_device_name:
      raise exceptions.ToolException(
          '[--boot-disk-device-name] can only be used when creating a new '
          'boot disk.')

    if args.boot_disk_type:
      raise exceptions.ToolException(
          '[--boot-disk-type] can only be used when creating a new boot '
          'disk.')

    if args.boot_disk_size:
      raise exceptions.ToolException(
          '[--boot-disk-size] can only be used when creating a new boot '
          'disk.')

    if not args.boot_disk_auto_delete:
      raise exceptions.ToolException(
          '[--no-boot-disk-auto-delete] can only be used when creating a '
          'new boot disk.')


def ValidateCreateDiskFlags(args):
  """Validates the values of create-disk related flags."""
  require_csek_key_create = getattr(args, 'require_csek_key_create', None)
  csek_key_file = getattr(args, 'csek_key_file', None)
  resource_names = getattr(args, 'names', [])
  for disk in getattr(args, 'create_disk', []) or []:
    disk_name = disk.get('name')
    if len(resource_names) > 1 and disk_name:
      raise exceptions.ToolException(
          'Cannot create a disk with [name]={} for more than one instance.'
          .format(disk_name))
    if not disk_name and require_csek_key_create and csek_key_file:
      raise exceptions.ToolException(
          'Cannot create a disk with customer supplied key when disk name '
          'is not specified.')

    mode_value = disk.get('mode')
    if mode_value and mode_value not in ('rw', 'ro'):
      raise exceptions.ToolException(
          'Value for [mode] in [--disk] must be [rw] or [ro], not [{0}].'
          .format(mode_value))

    image_value = disk.get('image')
    image_family_value = disk.get('image-family')
    if image_value and image_family_value:
      raise exceptions.ToolException(
          'Cannot specify [image] and [image-family] for a [--create-disk].'
          'The fields are mutually excusive.')
    if not image_value and not image_family_value:
      raise exceptions.ToolException(
          'Either [image] or [image-family] must be specified for '
          '[--create-disk].')


def AddAddressArgs(parser, instances=True,
                   multiple_network_interface_cards=False,
                   support_alias_ip_ranges=False):
  """Adds address arguments for instances and instance-templates."""
  addresses = parser.add_mutually_exclusive_group()
  addresses.add_argument(
      '--no-address',
      action='store_true',
      help=('If provided, the instances will not be assigned external IP '
            'addresses.'))
  address = addresses.add_argument(
      '--address',
      help='Assigns the given external address to the instance that is '
      'created.')
  if instances:
    address.detailed_help = """\
        Assigns the given external address to the instance that is created.
        The address may be an IP address or the name or URI of an address
        resource. This option can only be used when creating a single instance.
        """
  else:
    address.detailed_help = """\
        Assigns the given external IP address to the instance that is created.
        This option can only be used when creating a single instance.
        """
  multiple_network_interface_cards_spec = {
      'address': str,
      'network': str,
      'no-address': None,
      'subnet': str,
  }
  if instances:
    multiple_network_interface_cards_spec['private-network-ip'] = str
  if multiple_network_interface_cards:
    if support_alias_ip_ranges:
      multiple_network_interface_cards_spec['aliases'] = str
    network_interface = parser.add_argument(
        '--network-interface',
        type=arg_parsers.ArgDict(
            spec=multiple_network_interface_cards_spec,
            allow_key_only=True,
        ),
        action='append',  # pylint:disable=protected-access
        help='Adds a network interface to the instance.',
    )

    network_interface_detailed_help = """\
        Adds a network interface to the instance. Mutually exclusive with
        --address, --network, --subnet, and --private-network-ip flags.

        The following keys are allowed:
        *address*::: Assigns the given external address to the instance that is
        created. Specyfying an empty string will assign an ephemeral IP.
        Mutually exclusive with no-address. If neither key is present the
        instance will get an ephemeral IP.

        *network*::: Specifies the network that the interface will be part of.
        If subnet is also specified it must be subnetwork of this network. If
        neither is specified, this defaults to the "default" network.

        *no-address*::: If specified the interface will have no external IP.
        """
    if instances:
      network_interface_detailed_help += """
        *private-network-ip*::: Assigns the given RFC1918 IP address to the
        interface. """
    network_interface_detailed_help += """
        *subnet*::: Specifies the subnet that the interface will be part of.
        If network key is also specified this must be a subnetwork of the
        specified network."""
    if support_alias_ip_ranges:
      network_interface_detailed_help += """
        *aliases*::: Specifies the IP aliase ranges to allocate for this
        interface.  If there are multiple IP aliase ranges, they are seperated
        by semicolons. Currently, only one IP alias range is supported."""
      if instances:
        network_interface_detailed_help += """
          Each IP alias range consists of a range name and an IP range
          separated by a colon, or just the IP range.
          The range name is the name of the range within the network
          interface's subnet from which to allocate an IP alias range. If
          unspecified, it defaults to the primary IP range of the subnet.
          The IP range can be a CIDR range (e.g. 192.168.100.0/24), a single
          IP address (e.g. 192.168.100.1), or a net mask in CIDR format (e.g.
          /24). If the IP range is specified by CIDR range or single IP
          address, it must belong to the CIDR range specified by the range
          name on the subnet. If the IP range is specified by net mask, the
          IP allocator will pick an available range with the specified netmask
          and allocate it to this network interface."""
      else:
        network_interface_detailed_help += """
          Each IP alias range consists of a range name and an CIDR net mask
          (e.g. /24) separated by a colon, or just the net mask.
          The range name is the name of the range within the network
          interface's subnet from which to allocate an IP alias range. If
          unspecified, it defaults to the primary IP range of the subnet.
          IP allocator will pick an available range with the specified netmask
          and allocate it to this network interface."""
    network_interface.detailed_help = network_interface_detailed_help


def AddMachineTypeArgs(parser, required=False):
  machine_type = parser.add_argument(
      '--machine-type',
      completion_resource='compute.machineTypes',
      help='Specifies the machine type used for the instances.',
      required=required)
  machine_type.detailed_help = """\
      Specifies the machine type used for the instances. To get a
      list of available machine types, run 'gcloud compute
      machine-types list'. If unspecified, the default type is n1-standard-1.
      """


def AddPreemptibleVmArgs(parser):
  preemptible = parser.add_argument(
      '--preemptible',
      action='store_true',
      help='If provided, instances will be preemptible and time-limited.',
      default=False)
  preemptible.detailed_help = """\
      If provided, instances will be preemptible and time-limited.
      Instances may be preempted to free up resources for standard VM instances,
      and will only be able to run for a limited amount of time. Preemptible
      instances can not be restarted and will not migrate.
      """


def AddNetworkArgs(parser):
  """Set arguments for choosing the network/subnetwork."""
  network = parser.add_argument(
      '--network',
      help='Specifies the network that the instances will be part of.')

  network.detailed_help = """\
      Specifies the network that the instances will be part of. If --subnet is
      also specified subnet must be a subnetwork of network specified by
      --network. If neither is specified, this defaults to the "default"
      network.
      """

  subnet = parser.add_argument(
      '--subnet',
      help='Specifies the subnet that the instances will be part of.')
  subnet.detailed_help = """\
      Specifies the subnet that the instances will be part of. If --network is
      also specified subnet must be a subnetwork of network specified by
      --network.
      """


def AddPrivateNetworkIpArgs(parser):
  """Set arguments for choosing the network IP address."""
  private_network_ip = parser.add_argument(
      '--private-network-ip',
      help='Assigns the given RFC1918 IP address to the instance.')
  private_network_ip.detailed_help = """\
      Specifies the RFC1918 IP to assign to the instance. The IP should be in
      the subnet or legacy network IP range.
      """


def AddServiceAccountAndScopeArgs(parser, instance_exists):
  """Add args for configuring service account and scopes.

  This should replace AddScopeArgs (b/30802231).

  Args:
    parser: ArgumentParser, parser to which flags will be added.
    instance_exists: bool, If instance already exists and we are modifying it.
  """
  service_account_group = parser.add_mutually_exclusive_group()
  service_account_group.add_argument(
      '--no-service-account', action='store_true',
      help='Remove service account from the instance' if instance_exists
      else 'Create instance without service account')

  service_account = service_account_group.add_argument(
      '--service-account',
      help='Service account and scopes for the instances')
  sa_exists = 'keep the service account it currently has'
  sa_not_exists = 'get project\'s default service account'
  service_account.detailed_help = """\
  A service account is an identity attached to the instance. Its access tokens
  can be accessed through the instance metadata server and are used to
  authenticate applications on the instance. The account can be either an email
  address or an alias corresponding to a service account. You can explicitly
  specify the Compute Engine default service account using the 'default' alias.

  If not provided, the instance will {0}.
  """.format(sa_exists if instance_exists else sa_not_exists)

  scopes_group = parser.add_mutually_exclusive_group()
  scopes_group.add_argument(
      '--no-scopes', action='store_true',
      help='Remove all scopes from the instance' if instance_exists
      else 'Create instance without scopes')
  scopes = scopes_group.add_argument(
      '--scopes',
      type=arg_parsers.ArgList(),
      metavar='SCOPE',
      help='Comma separated list of scopes for the instance')
  scopes_exists = 'keep the scopes it currently has'
  scopes_not_exists = 'be assigned the default scopes, described below'
  scopes.detailed_help = """\
  If not provided, the instance will {0}.

  SCOPE can be either the full URI of the scope or an alias. Available
  aliases are:

    default
      Scopes assigned to instances by default:
      - https://www.googleapis.com/auth/cloud.useraccounts.readonly
      - https://www.googleapis.com/auth/devstorage.read_only
      - https://www.googleapis.com/auth/logging.write
      - https://www.googleapis.com/auth/monitoring.write
      - https://www.googleapis.com/auth/service.management.readonly
      - https://www.googleapis.com/auth/servicecontrol

    bigquery
      - https://www.googleapis.com/auth/bigquery

    cloud-platform
      - https://www.googleapis.com/auth/cloud-platform

    compute-ro
      - https://www.googleapis.com/auth/compute.readonly

    compute-rw
      - https://www.googleapis.com/auth/compute

    datastore
      - https://www.googleapis.com/auth/datastore

    logging-write
      - https://www.googleapis.com/auth/logging.write

    monitoring
      - https://www.googleapis.com/auth/monitoring

    monitoring-write
      - https://www.googleapis.com/auth/monitoring.write

    service-control
      - https://www.googleapis.com/auth/servicecontrol

    service-management
      - https://www.googleapis.com/auth/service.management.readonly

    sql
      - https://www.googleapis.com/auth/sqlservice

    sql-admin
      - https://www.googleapis.com/auth/sqlservice.admin

    storage-full
      - https://www.googleapis.com/auth/devstorage.full_control

    storage-ro
      - https://www.googleapis.com/auth/devstorage.read_only

    storage-rw
      - https://www.googleapis.com/auth/devstorage.read_write

    taskqueue
      - https://www.googleapis.com/auth/taskqueue

    useraccounts-ro
      - https://www.googleapis.com/auth/cloud.useraccounts.readonly

    useraccounts-rw
      - https://www.googleapis.com/auth/cloud.useraccounts

    userinfo-email
      - https://www.googleapis.com/auth/userinfo.email
    """.format(scopes_exists if instance_exists else scopes_not_exists)


def AddNetworkInterfaceArgs(parser):
  """Adds network interface flag to the argparse."""

  network_interface = parser.add_argument(
      '--network-interface',
      default=constants.DEFAULT_NETWORK_INTERFACE,
      action=arg_parsers.StoreOnceAction,
      help=('Specifies the name of the network interface which contains the'
            'access configuration.'))
  network_interface.detailed_help = """\
      Specifies the name of the network interface which contains the access
      configuration. If this is not provided, then "nic0" is used
      as the default.
      """


def AddPublicDnsArgs(parser, instance=True):
  """Adds public DNS arguments for instance or access configuration."""

  public_dns_args = parser.add_mutually_exclusive_group()
  no_public_dns = public_dns_args.add_argument(
      '--no-public-dns',
      action='store_true',
      help=(
          'If provided, the instance will not be assigned a public DNS name.'))
  if instance:
    no_public_dns.detailed_help = """\
        If provided, the instance will not be assigned a public DNS name.
        """
  else:
    no_public_dns.detailed_help = """\
        If provided, the external IP in the access configuration will not be
        assigned a public DNS name.
        """

  public_dns = public_dns_args.add_argument(
      '--public-dns',
      action='store_true',
      help='Assigns a public DNS name to the instance.')
  if instance:
    public_dns.detailed_help = """\
        Assigns a public DNS name to the instance.
        """
  else:
    public_dns.detailed_help = """\
        Assigns a public DNS name to the external IP in the access
        configuration. This option can only be specified for the default
        network-interface, "nic0".
        """

  public_ptr_args = parser.add_mutually_exclusive_group()
  no_public_ptr = public_ptr_args.add_argument(
      '--no-public-ptr',
      action='store_true',
      help=(
          'If provided, no DNS PTR record is created. Mutually exclusive with '
          'public-ptr-domain.'))
  if instance:
    no_public_ptr.detailed_help = """\
        If provided, no DNS PTR record is created for the external IP of the
        instance. Mutually exclusive with public-ptr-domain.
        """
  else:
    no_public_ptr.detailed_help = """\
        If provided, no DNS PTR record is created for the external IP in the
        access configuration. Mutually exclusive with public-ptr-domain.
        """

  public_ptr = public_ptr_args.add_argument(
      '--public-ptr',
      action='store_true',
      help='Creates a DNS PTR record for the external IP of the instance.')
  if instance:
    public_ptr.detailed_help = """\
        Creates a DNS PTR record for the external IP of the instance.
        """
  else:
    public_ptr.detailed_help = """\
        Creates a DNS PTR record for the external IP in the access
        configuration. This option can only be specified for the default
        network-interface, "nic0".
        """

  public_ptr_domain_args = parser.add_mutually_exclusive_group()
  no_public_ptr_domain = public_ptr_domain_args.add_argument(
      '--no-public-ptr-domain',
      action='store_true',
      help=(
          'If both this flag and --public-ptr are specified, creates a DNS PTR '
          'record for the external IP of the instance with the PTR domain name '
          'being the DNS name of the instance.'))
  if instance:
    no_public_ptr_domain.detailed_help = """\
        If both this flag and --public-ptr are specified, creates a DNS PTR
        record for the external IP of the instance with the PTR domain name
        being the DNS name of the instance.
        """
  else:
    no_public_ptr_domain.detailed_help = """\
        If both this flag and --public-ptr are specified, creates a DNS PTR
        record for the external IP in the access configuration with the PTR
        domain name being the DNS name of the instance.
        """

  public_ptr_domain = public_ptr_domain_args.add_argument(
      '--public-ptr-domain',
      help='Assigns a custom PTR domain for the external IP of the instance. '
      'Mutually exclusive with no-public-ptr.')
  if instance:
    public_ptr_domain.detailed_help = """\
        Assigns a custom PTR domain for the external IP of the instance.
        Mutually exclusive with no-public-ptr.
        """
  else:
    public_ptr_domain.detailed_help = """\
        Assigns a custom PTR domain for the external IP in the access
        configuration. Mutually exclusive with no-public-ptr. This option can
        only be specified for the default network-interface, "nic0".
        """


def ValidatePublicDnsFlags(args):
  """Validates the values of public DNS related flags."""

  network_interface = getattr(args, 'network_interface', None)
  public_dns = getattr(args, 'public_dns', None)
  public_ptr = getattr(args, 'public_ptr', None)
  if public_dns is True or public_ptr is True:
    if (network_interface is not None and
        network_interface != constants.DEFAULT_NETWORK_INTERFACE):
      raise exceptions.ToolException(
          'Public DNS can only be enabled for default network interface '
          '\'{0}\' rather than \'{1}\'.'.format(
              constants.DEFAULT_NETWORK_INTERFACE, network_interface))

  if args.public_ptr_domain is not None and args.no_public_ptr is True:
    raise exceptions.ConflictingArgumentsException('--public-ptr-domain',
                                                   '--no-public-ptr')


def ValidateServiceAccountAndScopeArgs(args):
  if args.no_service_account and not args.no_scopes:
    raise exceptions.RequiredArgumentException(
        '--no-scopes', 'required with argument '
        '--no-service-account')
  # Reject empty scopes
  for scope in (args.scopes or []):
    if not scope:
      raise exceptions.InvalidArgumentException(
          '--scopes', 'Scope cannot be an empty string.')


def AddTagsArgs(parser):
  tags = parser.add_argument(
      '--tags',
      type=arg_parsers.ArgList(min_length=1),
      help='A list of tags to apply to the instances.',
      metavar='TAG')
  tags.detailed_help = """\
      Specifies a list of tags to apply to the instances for
      identifying the instances to which network firewall rules will
      apply. See gcloud_compute_firewall-rules_create(1) for more
      details.
      """


def AddNoRestartOnFailureArgs(parser):
  restart_on_failure = parser.add_argument(
      '--restart-on-failure',
      action='store_true',
      default=True,
      help='Restart instances if they are terminated by Compute Engine.')
  restart_on_failure.detailed_help = """\
      The instances will be restarted if they are terminated by Compute Engine.
      This does not affect terminations performed by the user.
      """


def AddMaintenancePolicyArgs(parser):
  parser.add_argument(
      '--maintenance-policy',
      choices=MIGRATION_OPTIONS,
      type=lambda x: x.upper(),
      help=('Specifies the behavior of the instances when their host '
            'machines undergo maintenance. The default is MIGRATE.'))


def AddAcceleratorArgs(parser):
  """Adds Accelerator-related args."""
  # Attaches accelerators (e.g. GPUs) to the instances. e.g. --accelerator
  # type=nvidia-tesla-k80,count=4
  # TODO(b/34676942): METAVAR should be synthesized or it should not be needed
  # for ArgDict type of argument.
  accelerator = parser.add_argument(
      '--accelerator',
      type=arg_parsers.ArgDict(spec={
          'type': str,
          'count': int,
      }),
      metavar='type=TYPE,[count=COUNT]',
      help='Attaches accelerators (e.g. GPUs) to the instances.')
  accelerator.detailed_help = """
      Attaches accelerators (e.g. GPUs) to the instances.

      *type*::: The specific type (e.g. nvidia-tesla-k80 for nVidia Tesla K80)
      of accelerator to attach to the instances. Use 'gcloud compute
      accelerator-types list' to learn about all available accelerator types.

      *count*::: The number of pieces of the accelerator to attach to the
      instances. The default value is 1.
      """


def ValidateAcceleratorArgs(args):
  """Valiadates flags specyfying accelerators (e.g. GPUs).

  Args:
    args: parsed comandline arguments.
  Raises:
    InvalidArgumentException: when type is not specified in the accelerator
    config dictionary.
  """
  accelerator_args = getattr(args, 'accelerator', None)
  if accelerator_args:
    accelerator_type_name = accelerator_args.get('type', '')
    if not accelerator_type_name:
      raise exceptions.InvalidArgumentException(
          '--accelerator', 'accelerator type must be specified. '
          'e.g. --accelerator type=nvidia-tesla-k80,count=2')


def AddDockerArgs(parser):
  """Adds Docker-related args."""
  docker_image = parser.add_argument(
      '--docker-image',
      help=('Docker image URL to run on VM.'))
  docker_image.detailed_help = """\
  The URL to a Docker image to run on this instance. For example:
      gcr.io/google-containers/busybox
  """

  parser.add_argument('--container-manifest', help=argparse.SUPPRESS)

  run_command = parser.add_argument(
      '--run-command',
      help=('Run command for given Docker image.'))
  run_command.detailed_help = """\
  Command to be executed when running the Docker image. The command is
  specified in shell form:

    command param1 param2 ...

  It is possible to quote and escape params, for example:

    $ {command} --run-command='echo "Hello world"'

  Command will result in error on wrong syntax for this parameter.
  """

  run_as_privileged = parser.add_argument(
      '--run-as-privileged',
      action='store_true',
      help=('Whether container should be run in privileged mode.'))
  run_as_privileged.detailed_help = """\
  Privileged mode is useful for containers that want to use linux capabilities
  like manipulating the network stack and accessing devices.
  With this argument specified Docker will enable to access to all devices on
  the host as well as set some configuration in AppArmor or SELinux
  to allow the container nearly all the same access to the host as processes
  running outside containers on the host.
  """

  port_mappings = parser.add_argument(
      '--port-mappings',
      type=arg_parsers.ArgList(),
      metavar='PORT:TARGET_PORT:PROTOCOL',
      help=('Port mapping for container.'))
  port_mappings.detailed_help = """\
  Configure bindings of container ports to the host ports.
  Value of this parameter should be comma-separated list of
  port1:port2:protocol triads representing host port, container port and
  protocol. Protocol could be: {0}.

  For example following command:

    $ {{command}} --port-mappings=80:8888:TCP

  will expose container port 8888 on port 80 of VM. This binding will serve TCP
  traffic.
  """.format(', '.join(containers_utils.ALLOWED_PROTOCOLS))


def ValidateDockerArgs(args):
  """Validates Docker-related args."""
  if not args.container_manifest and not args.docker_image:
    raise exceptions.RequiredArgumentException(
        '--docker-image', 'You must provide Docker image')

  if args.container_manifest:
    log.warn('--container-manifest flag is deprecated and will be removed. '
             'Use --docker-image flag instead.')

    if args.run_command:
      raise exceptions.InvalidArgumentException(
          '--run-command', 'argument --run-command: not allowed with argument '
          '--container-manifest')
    if args.port_mappings:
      raise exceptions.InvalidArgumentException(
          '--port-mappings', 'argument --port-mappings: not allowed with '
          'argument --container-manifest')


def ValidateLocalSsdFlags(args):
  for local_ssd in args.local_ssd or []:
    interface = local_ssd.get('interface')
    if interface and interface not in LOCAL_SSD_INTERFACES:
      raise exceptions.InvalidArgumentException(
          '--local-ssd:interface', 'Unexpected local SSD interface: [{given}]. '
          'Legal values are [{ok}].'
          .format(given=interface,
                  ok=', '.join(LOCAL_SSD_INTERFACES)))


def ValidateNicFlags(args):
  """Valiadates flags specyfying network interface cards.

  Args:
    args: parsed comandline arguments.
  Raises:
    InvalidArgumentException: when it finds --network-interface that has both
                              address, and no-address keys.
    ConflictingArgumentsException: when it finds --network-interface and at
                                   least one of --address, --network,
                                   --private_network_ip, or --subnet.
  """
  network_interface = getattr(args, 'network_interface', None)
  if network_interface is None:
    return
  for ni in network_interface:
    if 'address' in ni and 'no-address' in ni:
      raise exceptions.InvalidArgumentException(
          '--network-interface',
          'specifies both address and no-address for one interface')

  conflicting_args = [
      'address', 'network', 'private_network_ip', 'subnet']
  conflicting_args_present = [
      arg for arg in conflicting_args if getattr(args, arg, None)]
  if not conflicting_args_present:
    return
  conflicting_args = ['--{0}'.format(arg.replace('_', '-'))
                      for arg in conflicting_args_present]
  raise exceptions.ConflictingArgumentsException(
      '--network-interface',
      'all of the following: ' + ', '.join(conflicting_args))


def AddDiskScopeFlag(parser):
  """Adds --disk-scope flag."""
  parser.add_argument(
      '--disk-scope',
      choices={'zonal':
               'The disk specified in --disk is interpreted as a '
               'zonal disk in the same zone as the instance',
               'regional':
               'The disk specified in --disk is interpreted as a '
               'regional disk in the same region as the instance'},
      help='The scope of the disk.',
      hidden=True,
      default='zonal')
