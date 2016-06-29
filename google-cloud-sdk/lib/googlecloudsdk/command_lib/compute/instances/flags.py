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
import ipaddr

MIGRATION_OPTIONS = ['MIGRATE', 'TERMINATE']

LOCAL_SSD_INTERFACES = ['NVME', 'SCSI']

DISK_METAVAR = (
    'name=NAME [mode={ro,rw}] [boot={yes,no}] [device-name=DEVICE_NAME] '
    '[auto-delete={yes,no}]')


def AddImageArgs(parser):
  """Adds arguments related to images for instances and instance-templates."""

  def AddImageHelp():
    """Returns the detailed help for the `--image` flag."""
    template = """
          Specifies the boot image for the instances. For each
          instance, a new boot disk will be created from the given
          image. Each boot disk will have the same name as the
          instance.

          When using this option, ``--boot-disk-device-name'' and
          ``--boot-disk-size'' can be used to override the boot disk's
          device name and size, respectively.

          By default, ``{default_image}'' is assumed for this flag.
          """
    return template.format(default_image=constants.DEFAULT_IMAGE)

  image_group = parser.add_mutually_exclusive_group()
  image = image_group.add_argument(
      '--image',
      help='The image that the boot disk will be initialized with.',
      metavar='IMAGE')
  image.detailed_help = AddImageHelp
  image_utils.AddImageProjectFlag(parser)

  image_group.add_argument(
      '--image-family',
      help=('The family of the image that the boot disk will be initialized '
            'with. When a family is specified instead of an image, the latest '
            'non-deprecated image associated with that family is used.')
  )


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
      action=arg_parsers.FloatingListValuesCatcher(
          argparse._AppendAction,  # pylint:disable=protected-access
          switch_value={}),
      help='(BETA) Specifies instances with attached local SSDs.',
      metavar='PROPERTY=VALUE')
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


def AddDiskArgs(parser):
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

  disk = parser.add_argument(
      '--disk',
      type=arg_parsers.ArgDict(spec={
          'name': str,
          'mode': str,
          'boot': str,
          'device-name': str,
          'auto-delete': str,
      }),
      action=arg_parsers.FloatingListValuesCatcher(argparse._AppendAction),  # pylint:disable=protected-access
      help='Attaches persistent disks to the instances.',
      metavar='PROPERTY=VALUE')
  disk.detailed_help = """
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


def ExpandAddressFlag(scope_prompter, compute_client, address, region):
  """Resolves the --address flag value.

  If the value of --address is a name, the regional address is queried.

  Args:
    scope_prompter: Scope prompter object,
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
  address_ref = scope_prompter.CreateRegionalReference(
      address, region, resource_type='addresses')
  res = _GetAddress(compute_client, address_ref)
  return res.address


def ValidateDiskFlags(args):
  """Validates the values of all disk-related flags."""
  ValidateDiskCommonFlags(args)
  ValidateDiskAccessModeFlags(args)
  ValidateDiskBootFlags(args)


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


def AddAddressArgs(parser, instances=True):
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
  netparser = parser.add_mutually_exclusive_group()

  network = netparser.add_argument(
      '--network',
      default=constants.DEFAULT_NETWORK,
      help='Specifies the network that the instances will be part of.')

  network.detailed_help = """\
      Specifies the network that the instances will be part of. This is mutually
      exclusive with --subnet. If neither is specified, this defaults to the
      "default" network.
      """

  subnet = netparser.add_argument(
      '--subnet',
      help='Specifies the subnet that the instances will be part of.')
  subnet.detailed_help = """\
      Specifies the subnet that the instances will be part of. This is mutally
      exclusive with --network.
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


def AddScopeArgs(parser):
  """Adds scope arguments for instances and instance-templates."""
  scopes_group = parser.add_mutually_exclusive_group()

  def AddScopesHelp():
    return """\
        Specifies service accounts and scopes for the
        instances. Service accounts generate access tokens that can be
        accessed through the instance metadata server and used to
        authenticate applications on the instance. The account can be
        either an email address or an alias corresponding to a
        service account. If account is omitted, the project's default
        service account is used. The default service account can be
        specified explicitly by using the alias ``default''. Example:

          $ {{command}} example-instance --scopes compute-rw,me@project.gserviceaccount.com=storage-rw

        If this flag is not provided, the following scopes are used:
        {default_scopes}. To create instances with no scopes, use
        ``--no-scopes'':

          $ {{command}} example-instance --no-scopes

        SCOPE can be either the full URI of the scope or an
        alias. Available aliases are:

        [options="header",format="csv",grid="none",frame="none"]
        |========
        Alias,URI
        {aliases}
        |========
        """.format(
            default_scopes=', '.join(constants.DEFAULT_SCOPES),
            aliases='\n        '.join(
                ','.join(value) for value in
                sorted(constants.SCOPES.iteritems())))
  scopes = scopes_group.add_argument(
      '--scopes',
      type=arg_parsers.ArgList(min_length=1),
      action=arg_parsers.FloatingListValuesCatcher(),
      help='Specifies service accounts and scopes for the instances.',
      metavar='[ACCOUNT=]SCOPE')
  scopes.detailed_help = AddScopesHelp

  scopes_group.add_argument(
      '--no-scopes',
      action='store_true',
      help=('If provided, the default scopes ({scopes}) are not added to the '
            'instances.'.format(scopes=', '.join(constants.DEFAULT_SCOPES))))


def AddTagsArgs(parser):
  tags = parser.add_argument(
      '--tags',
      type=arg_parsers.ArgList(min_length=1),
      action=arg_parsers.FloatingListValuesCatcher(),
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
  maintenance_policy = parser.add_argument(
      '--maintenance-policy',
      choices=MIGRATION_OPTIONS,
      type=lambda x: x.upper(),
      help=('Specifies the behavior of the instances when their host '
            'machines undergo maintenance.'))
  maintenance_policy.detailed_help = """\
      Specifies the behavior of the instances when their host machines
      undergo maintenance. ``TERMINATE'' indicates that the instances
      should be terminated. ``MIGRATE'' indicates that the instances
      should be migrated to a new host. Choosing ``MIGRATE'' will
      temporarily impact the performance of instances during a
      migration event. If omitted, ``MIGRATE'' is assumed.
      """


def AddDockerArgs(parser):
  """Adds Docker-related args."""
  docker_spec_group = parser.add_mutually_exclusive_group(required=True)
  docker_image = docker_spec_group.add_argument(
      '--docker-image',
      help=('Docker image URL to run on VM.'))
  docker_image.detailed_help = """\
  The URL to a Docker image to run on this instance. For example:
      gcr.io/google-containers/busybox
  """

  container_manifest = docker_spec_group.add_argument(
      '--container-manifest',
      help=('Container manifest to run on VM.'))
  container_manifest.detailed_help = """\
  Container deployment specification, conforming to Kubernetes podspec format:
      http://kubernetes.io/docs/user-guide/deployments/

  When specified, --run-command, --run-as-privileged, and --port-mappings cannot
  be used. Instead, if needed, those options must be provided with the container
  manifest.
  """

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
  if args.container_manifest:
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
