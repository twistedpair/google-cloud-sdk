# Copyright 2014 Google Inc. All Rights Reserved.
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
"""Convenience functions for dealing with instances and instance templates."""
import collections
import re

from googlecloudsdk.api_lib.compute import alias_ip_range_utils
from googlecloudsdk.api_lib.compute import constants
from googlecloudsdk.api_lib.compute import csek_utils
from googlecloudsdk.api_lib.compute import image_utils
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.compute import scope as compute_scopes
from googlecloudsdk.command_lib.compute.instances import flags
from googlecloudsdk.command_lib.util.ssh import ssh
from googlecloudsdk.core import log
import ipaddr


EMAIL_REGEX = re.compile(r'(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)')


def GetCpuRamFromCustomName(name):
  """Gets the CPU and memory specs from the custom machine type name.

  Args:
    name: the custom machine type name for the 'instance create' call

  Returns:
    A two-tuple with the number of cpu and amount of memory for the custom
    machine type

    custom_cpu, the number of cpu desired for the custom machine type instance
    custom_memory_mib, the amount of ram desired in MiB for the custom machine
      type instance
    None for both variables otherwise
  """
  check_custom = re.search('custom-([0-9]+)-([0-9]+)', name)
  if check_custom:
    custom_cpu = check_custom.group(1)
    custom_memory_mib = check_custom.group(2)
    return custom_cpu, custom_memory_mib
  return None, None


def GetNameForCustom(custom_cpu, custom_memory_mib, ext=False):
  """Creates a custom machine type name from the desired CPU and memory specs.

  Args:
    custom_cpu: the number of cpu desired for the custom machine type
    custom_memory_mib: the amount of ram desired in MiB for the custom machine
      type instance
    ext: extended custom machine type should be used if true

  Returns:
    The custom machine type name for the 'instance create' call
  """
  machine_type = 'custom-{0}-{1}'.format(custom_cpu, custom_memory_mib)
  if ext:
    machine_type += '-ext'
  return machine_type


def InterpretMachineType(machine_type, custom_cpu, custom_memory, ext=True):
  """Interprets the machine type for the instance.

  Args:
    machine_type: name of existing machine type, eg. n1-standard
    custom_cpu: number of CPU cores for custom machine type,
    custom_memory: amount of RAM memory in bytes for custom machine type,
    ext: extended custom machine type should be used if true,

  Returns:
    A string representing the URL naming a machine-type.

  Raises:
    exceptions.RequiredArgumentException when only one of the two custom
      machine type flags are used.
    exceptions.InvalidArgumentException when both the machine type and
      custom machine type flags are used to generate a new instance.
  """
  # Setting the machine type
  machine_type_name = constants.DEFAULT_MACHINE_TYPE
  if machine_type:
    machine_type_name = machine_type

  # Setting the specs for the custom machine.
  if custom_cpu or custom_memory or ext:
    if not custom_cpu:
      raise exceptions.RequiredArgumentException(
          '--custom-cpu', 'Both [--custom-cpu] and [--custom-memory] must be '
          'set to create a custom machine type instance.')
    if not custom_memory:
      raise exceptions.RequiredArgumentException(
          '--custom-memory', 'Both [--custom-cpu] and [--custom-memory] must '
          'be set to create a custom machine type instance.')
    if machine_type:
      raise exceptions.InvalidArgumentException(
          '--machine-type', 'Cannot set both [--machine-type] and '
          '[--custom-cpu]/[--custom-memory] for the same instance.')
    custom_type_string = GetNameForCustom(
        custom_cpu,
        # converting from B to MiB.
        int(custom_memory / (2 ** 20)),
        ext)

    # Updating the machine type that is set for the URIs
    machine_type_name = custom_type_string
  return machine_type_name


def CheckCustomCpuRamRatio(compute_client, project, zone, machine_type_name):
  """Checks that the CPU and memory ratio is a supported custom instance type.

  Args:
    compute_client: GCE API client,
    project: a project,
    zone: the zone of the instance(s) being created,
    machine_type_name: The machine type of the instance being created.

  Returns:
    Nothing. Function acts as a bound checker, and will raise an exception from
      within the function if needed.

  Raises:
    utils.RaiseToolException if a custom machine type ratio is out of bounds.
  """
  messages = compute_client.messages
  compute = compute_client.apitools_client
  if 'custom' in machine_type_name:
    mt_get_pb = messages.ComputeMachineTypesGetRequest(
        machineType=machine_type_name,
        project=project,
        zone=zone)
    mt_get_reqs = [(compute.machineTypes, 'Get', mt_get_pb)]
    errors = []

    # Makes a 'machine-types describe' request to check the bounds
    _ = list(compute_client.MakeRequests(
        requests=mt_get_reqs,
        errors_to_collect=errors))

    if errors:
      utils.RaiseToolException(
          errors,
          error_message='Could not fetch machine type:')


def CreateServiceAccountMessages(messages, scopes, service_account):
  """Returns a list of ServiceAccount messages corresponding to scopes."""
  silence_deprecation_warning = False
  if scopes is None:
    scopes = constants.DEFAULT_SCOPES
  # if user provided --no-service-account, it is already verified that
  # scopes == [] and thus service_account value will not be used
  service_account_specified = service_account is not None
  if service_account is None:
    service_account = 'default'

  accounts_to_scopes = collections.defaultdict(list)
  for scope in scopes:
    parts = scope.split('=')
    if len(parts) == 1:
      account = service_account
      scope_uri = scope
    elif len(parts) == 2:
      account, scope_uri = parts
      if service_account_specified:
        raise exceptions.InvalidArgumentException(
            '--scopes',
            'It is illegal to mix old --scopes flag format '
            '[--scopes {0}={1}] with [--service-account ACCOUNT] flag. Use '
            '[--scopes {1} --service-account {2}] instead.'
            .format(account, scope_uri, service_account))
      # TODO(b/33688878) Remove support for this deprecated format
      if not silence_deprecation_warning:
        log.warning(
            'Flag format --scopes [ACCOUNT=]SCOPE, [[ACCOUNT=]SCOPE, ...] is '
            'deprecated and will be removed 24th Jan 2018. Use --scopes SCOPE'
            '[, SCOPE...] --service-account ACCOUNT instead.')
        silence_deprecation_warning = True  # Do not warn again for each scope
    else:
      raise exceptions.ToolException(
          '[{0}] is an illegal value for [--scopes]. Values must be of the '
          'form [SCOPE] or [ACCOUNT=SCOPE].'.format(scope))

    if service_account != 'default' and not ssh.Remote.FromArg(service_account):
      raise exceptions.InvalidArgumentException(
          '--service-account',
          'Invalid format: expected default or user@domain.com, received ' +
          service_account)

    # Expands the scope if the user provided an alias like
    # "compute-rw".
    scope_uri = constants.SCOPES.get(scope_uri, [scope_uri])
    accounts_to_scopes[account].extend(scope_uri)

  res = []
  for account, scopes in sorted(accounts_to_scopes.iteritems()):
    res.append(messages.ServiceAccount(email=account,
                                       scopes=sorted(scopes)))
  return res


def CreateOnHostMaintenanceMessage(messages, maintenance_policy):
  """Create on-host-maintenance message for VM."""
  if maintenance_policy:
    on_host_maintenance = messages.Scheduling.OnHostMaintenanceValueValuesEnum(
        maintenance_policy)
  else:
    on_host_maintenance = None
  return on_host_maintenance


def CreateSchedulingMessage(
    messages, maintenance_policy, preemptible, restart_on_failure):
  """Create scheduling message for VM."""
  # Note: We always specify automaticRestart=False for preemptible VMs. This
  # makes sense, since no-restart-on-failure is defined as "store-true", and
  # thus can't be given an explicit value. Hence it either has its default
  # value (in which case we override it for convenience's sake to the only
  # setting that makes sense for preemptible VMs), or the user actually
  # specified no-restart-on-failure, the only usable setting.
  on_host_maintenance = CreateOnHostMaintenanceMessage(messages,
                                                       maintenance_policy)
  if preemptible:
    scheduling = messages.Scheduling(automaticRestart=False,
                                     onHostMaintenance=on_host_maintenance,
                                     preemptible=True)
  else:
    scheduling = messages.Scheduling(automaticRestart=restart_on_failure,
                                     onHostMaintenance=on_host_maintenance)
  return scheduling


def CreateMachineTypeUris(
    resources, compute_client,
    machine_type, custom_cpu, custom_memory, ext, instance_refs):
  """Create machine type URIs for given args and instance references."""
  # The element at index i is the machine type URI for instance
  # i. We build this list here because we want to delay work that
  # requires API calls as much as possible. This leads to a better
  # user experience because the tool can fail fast upon a spelling
  # mistake instead of delaying the user by making API calls whose
  # purpose has already been rendered moot by the spelling mistake.
  machine_type_uris = []

  # Setting the machine type
  machine_type_name = InterpretMachineType(
      machine_type, custom_cpu, custom_memory, ext)

  for instance_ref in instance_refs:
    # Check to see if the custom machine type ratio is supported
    CheckCustomCpuRamRatio(compute_client,
                           instance_ref.project,
                           instance_ref.zone,
                           machine_type_name)
    machine_type_uris.append(
        resources.Parse(
            machine_type_name,
            collection='compute.machineTypes',
            params={
                'project': instance_ref.project,
                'zone': instance_ref.zone
            }).SelfLink())

  return machine_type_uris


def CreateNetworkInterfaceMessage(resources,
                                  compute_client,
                                  network,
                                  subnet,
                                  private_network_ip,
                                  no_address,
                                  address,
                                  instance_refs,
                                  alias_ip_ranges_string=None,
                                  network_tier=None,
                                  no_public_dns=None,
                                  public_dns=None,
                                  no_public_ptr=None,
                                  public_ptr=None,
                                  no_public_ptr_domain=None,
                                  public_ptr_domain=None):
  """Returns a new NetworkInterface message."""
  # TODO(b/30460572): instance reference should have zone name, not zone URI.
  region = utils.ZoneNameToRegionName(instance_refs[0].zone.split('/')[-1])
  messages = compute_client.messages
  network_interface = messages.NetworkInterface()
  # By default interface is attached to default network. If network or subnet
  # are specified they're used instead.
  if subnet is not None:
    subnet_ref = resources.Parse(
        subnet,
        collection='compute.subnetworks',
        params={
            'project': instance_refs[0].project,
            'region': region
        })
    network_interface.subnetwork = subnet_ref.SelfLink()
  if network is not None:
    network_ref = resources.Parse(
        network,
        params={
            'project': instance_refs[0].project,
        },
        collection='compute.networks')
    network_interface.network = network_ref.SelfLink()
  elif subnet is None:
    network_ref = resources.Parse(
        constants.DEFAULT_NETWORK,
        params={'project': instance_refs[0].project},
        collection='compute.networks')
    network_interface.network = network_ref.SelfLink()

  if private_network_ip is not None:
    # Try interpreting the address as IPv4 or IPv6.
    try:
      ipaddr.IPAddress(private_network_ip)
      network_interface.networkIP = private_network_ip
    except ValueError:
      # ipaddr could not resolve as an IPv4 or IPv6 address.
      network_interface.networkIP = flags.GetAddressRef(
          resources, private_network_ip, region).SelfLink()

  if alias_ip_ranges_string:
    network_interface.aliasIpRanges = (
        alias_ip_range_utils.CreateAliasIpRangeMessagesFromString(
            messages, True, alias_ip_ranges_string))

  if not no_address:
    access_config = messages.AccessConfig(
        name=constants.DEFAULT_ACCESS_CONFIG_NAME,
        type=messages.AccessConfig.TypeValueValuesEnum.ONE_TO_ONE_NAT)
    if network_tier is not None:
      access_config.networkTier = (messages.AccessConfig.
                                   NetworkTierValueValuesEnum(network_tier))

    # If the user provided an external IP, populate the access
    # config with it.
    # TODO(b/25278937): plays poorly when creating multiple instances
    if len(instance_refs) == 1:
      address_resource = flags.ExpandAddressFlag(
          resources, compute_client, address, region)
      if address_resource:
        access_config.natIP = address_resource

    if no_public_dns is True:
      access_config.setPublicDns = False
    elif public_dns is True:
      access_config.setPublicDns = True

    if no_public_ptr is True:
      access_config.setPublicPtr = False
    elif public_ptr is True:
      access_config.setPublicPtr = True

    if no_public_ptr_domain is not True and public_ptr_domain is not None:
      access_config.publicPtrDomainName = public_ptr_domain

    network_interface.accessConfigs = [access_config]

  return network_interface


def CreateNetworkInterfaceMessages(resources, compute_client,
                                   network_interface_arg, instance_refs,
                                   support_network_tier):
  """Create network interface messages.

  Args:
    resources: generates resource references.
    compute_client: creates resources.
    network_interface_arg: CLI argument specyfying network interfaces.
    instance_refs: reference to instances that will own the generated
                   interfaces.
    support_network_tier: indicates if network tier is supported.
  Returns:
    list, items are NetworkInterfaceMessages.
  """
  result = []
  if network_interface_arg:
    for interface in network_interface_arg:
      address = interface.get('address', None)
      no_address = 'no-address' in interface
      if support_network_tier:
        network_tier = interface.get('network-tier',
                                     constants.DEFAULT_NETWORK_TIER)
      else:
        network_tier = None

      result.append(CreateNetworkInterfaceMessage(
          resources, compute_client, interface.get('network', None),
          interface.get('subnet', None),
          interface.get('private-network-ip', None), no_address,
          address, instance_refs, interface.get('aliases', None), network_tier))
  return result


def ParseDiskResource(resources, name, project, zone, type_):
  if type_ == compute_scopes.ScopeEnum.REGION:
    return resources.Parse(
        name,
        collection='compute.regionDisks',
        params={
            'project': project,
            'region': utils.ZoneNameToRegionName(zone)
        })
  else:
    return resources.Parse(
        name,
        collection='compute.disks',
        params={
            'project': project,
            'zone': zone
        })


def CreatePersistentAttachedDiskMessages(
    resources, compute_client, csek_keys, disks, instance_ref):
  """Returns a list of AttachedDisk messages and the boot disk's reference."""
  disks_messages = []
  boot_disk_ref = None

  messages = compute_client.messages
  compute = compute_client.apitools_client
  for disk in disks:
    name = disk['name']

    # Resolves the mode.
    mode_value = disk.get('mode', 'rw')
    if mode_value == 'rw':
      mode = messages.AttachedDisk.ModeValueValuesEnum.READ_WRITE
    else:
      mode = messages.AttachedDisk.ModeValueValuesEnum.READ_ONLY

    boot = disk.get('boot') == 'yes'
    auto_delete = disk.get('auto-delete') == 'yes'

    if 'scope' in disk and disk['scope'] == 'regional':
      scope = compute_scopes.ScopeEnum.REGION
    else:
      scope = compute_scopes.ScopeEnum.ZONE
    disk_ref = ParseDiskResource(resources, name, instance_ref.project,
                                 instance_ref.zone, scope)

    if boot:
      boot_disk_ref = disk_ref

    # TODO(b/36051031) drop test after CSEK goes GA
    if csek_keys:
      disk_key_or_none = csek_utils.MaybeLookupKeyMessage(
          csek_keys, disk_ref, compute)
      kwargs = {'diskEncryptionKey': disk_key_or_none}
    else:
      kwargs = {}

    attached_disk = messages.AttachedDisk(
        autoDelete=auto_delete,
        boot=boot,
        deviceName=disk.get('device-name'),
        mode=mode,
        source=disk_ref.SelfLink(),
        type=messages.AttachedDisk.TypeValueValuesEnum.PERSISTENT,
        **kwargs)

    # The boot disk must end up at index 0.
    if boot:
      disks_messages = [attached_disk] + disks_messages
    else:
      disks_messages.append(attached_disk)

  return disks_messages, boot_disk_ref


def CreatePersistentCreateDiskMessages(compute_client,
                                       resources, csek_keys, create_disks,
                                       instance_ref):
  """Returns a list of AttachedDisk messages for newly creating disks.

  Args:
    compute_client: creates resources,
    resources: parser of resources,
    csek_keys: customer suplied encryption keys,
    create_disks: disk objects - contains following properties
             * name - the name of disk,
             * mode - 'rw' (R/W), 'ro' (R/O) access mode,
             * disk-size - the size of the disk,
             * disk-type - the type of the disk (HDD or SSD),
             * image - the name of the image to initialize from,
             * image-family - the image family name,
             * image-project - the project name that has the image,
             * auto-delete - whether disks is deleted when VM is deleted,
             * device-name - device name on VM.
    instance_ref: reference to the instance that will own the new disks.
  Returns:
    list of API messages for attached disks
  """
  disks_messages = []

  messages = compute_client.messages
  compute = compute_client.apitools_client
  for disk in create_disks or []:
    name = disk.get('name')

    # Resolves the mode.
    mode_value = disk.get('mode', 'rw')
    if mode_value == 'rw':
      mode = messages.AttachedDisk.ModeValueValuesEnum.READ_WRITE
    else:
      mode = messages.AttachedDisk.ModeValueValuesEnum.READ_ONLY

    auto_delete_value = disk.get('auto-delete', 'yes')
    auto_delete = auto_delete_value == 'yes'

    disk_size_gb = utils.BytesToGb(disk.get('size'))
    disk_type = disk.get('type')
    if disk_type:
      disk_type_ref = resources.Parse(disk_type,
                                      collection='compute.diskTypes',
                                      params={
                                          'project': instance_ref.project,
                                          'zone': instance_ref.zone
                                      })

      disk_type_uri = disk_type_ref.SelfLink()
    else:
      disk_type_ref = None
      disk_type_uri = None

    image_expander = image_utils.ImageExpander(compute_client,
                                               resources)
    image_uri, _ = image_expander.ExpandImageFlag(
        user_project=instance_ref.project,
        image=disk.get('image'),
        image_family=disk.get('image-family'),
        image_project=disk.get('image-project'),
        return_image_resource=False)

    image_key = None
    disk_key = None
    if csek_keys:
      image_key = csek_utils.MaybeLookupKeyMessagesByUri(csek_keys,
                                                         resources,
                                                         [image_uri],
                                                         compute)
      if name:
        disk_ref = resources.Parse(name,
                                   collection='compute.disks',
                                   params={'zone': instance_ref.zone})
        disk_key = csek_utils.MaybeLookupKeyMessage(csek_keys, disk_ref,
                                                    compute)

    create_disk = messages.AttachedDisk(
        autoDelete=auto_delete,
        boot=False,
        deviceName=disk.get('device-name'),
        initializeParams=messages.AttachedDiskInitializeParams(
            diskName=name,
            sourceImage=image_uri,
            diskSizeGb=disk_size_gb,
            diskType=disk_type_uri,
            sourceImageEncryptionKey=image_key),
        mode=mode,
        type=messages.AttachedDisk.TypeValueValuesEnum.PERSISTENT,
        diskEncryptionKey=disk_key)

    disks_messages.append(create_disk)

  return disks_messages


def CreateAcceleratorConfigMessages(msgs, accelerator_type_ref,
                                    accelerator_count):
  """Returns a list of accelerator config messages.

  Args:
    msgs: tracked GCE API messages.
    accelerator_type_ref: reference to the accelerator type.
    accelerator_count: number of accelerators to attach to the VM.

  Returns:
    a list of accelerator config message that specifies the type and number of
    accelerators to attach to an instance.
  """

  accelerator_config = msgs.AcceleratorConfig(
      acceleratorType=accelerator_type_ref.SelfLink(),
      acceleratorCount=accelerator_count)
  return [accelerator_config]


def CreateDefaultBootAttachedDiskMessage(
    compute_client, resources, disk_type, disk_device_name, disk_auto_delete,
    disk_size_gb, require_csek_key_create, image_uri, instance_ref,
    csek_keys=None):
  """Returns an AttachedDisk message for creating a new boot disk."""
  messages = compute_client.messages
  compute = compute_client.apitools_client

  if disk_type:
    disk_type_ref = resources.Parse(
        disk_type,
        collection='compute.diskTypes',
        params={
            'project': instance_ref.project,
            'zone': instance_ref.zone
        })
    disk_type_uri = disk_type_ref.SelfLink()
  else:
    disk_type_ref = None
    disk_type_uri = None

  if csek_keys:
    # If we're going to encrypt the boot disk make sure that we select
    # a name predictably, instead of letting the API deal with name
    # conflicts automatically.
    #
    # Note that when csek keys are being used we *always* want force this
    # even if we don't have any encryption key for default disk name.
    #
    # Consider the case where the user's key file has a key for disk `foo-1`
    # and no other disk.  Assume she runs
    #   gcloud compute instances create foo --csek-key-file f \
    #       --no-require-csek-key-create
    # and gcloud doesn't force the disk name to be `foo`.  The API might
    # select name `foo-1` for the new disk, but has no way of knowing
    # that the user has a key file mapping for that disk name.  That
    # behavior violates the principle of least surprise.
    #
    # Instead it's better for gcloud to force a specific disk name in the
    # instance create, and fail if that name isn't available.

    effective_boot_disk_name = (
        disk_device_name or instance_ref.Name())

    disk_ref = resources.Parse(effective_boot_disk_name,
                               collection='compute.disks',
                               params={
                                   'project': instance_ref.project,
                                   'zone': instance_ref.zone
                               })
    disk_key_or_none = csek_utils.MaybeToMessage(
        csek_keys.LookupKey(disk_ref, require_csek_key_create),
        compute)
    [image_key_or_none] = csek_utils.MaybeLookupKeyMessagesByUri(
        csek_keys, resources, [image_uri], compute)
    kwargs_init_parms = {'sourceImageEncryptionKey': image_key_or_none}
    kwargs_disk = {'diskEncryptionKey': disk_key_or_none}
  else:
    kwargs_disk = {}
    kwargs_init_parms = {}
    effective_boot_disk_name = disk_device_name

  return messages.AttachedDisk(
      autoDelete=disk_auto_delete,
      boot=True,
      deviceName=effective_boot_disk_name,
      initializeParams=messages.AttachedDiskInitializeParams(
          sourceImage=image_uri,
          diskSizeGb=disk_size_gb,
          diskType=disk_type_uri,
          **kwargs_init_parms),
      mode=messages.AttachedDisk.ModeValueValuesEnum.READ_WRITE,
      type=messages.AttachedDisk.TypeValueValuesEnum.PERSISTENT,
      **kwargs_disk)


def UseExistingBootDisk(disks):
  """Returns True if the user has specified an existing boot disk."""
  return any(disk.get('boot') == 'yes' for disk in disks)


def CreateLocalSsdMessage(resources, messages, device_name, interface,
                          size_bytes=None, zone=None, project=None):
  """Create a message representing a local ssd."""

  if zone:
    disk_type_ref = resources.Parse(
        'local-ssd',
        collection='compute.diskTypes',
        params={
            'project': project,
            'zone': zone
        }
    )
    disk_type = disk_type_ref.SelfLink()
  else:
    disk_type = 'local-ssd'

  maybe_interface_enum = (
      messages.AttachedDisk.InterfaceValueValuesEnum(interface)
      if interface else None)

  local_ssd = messages.AttachedDisk(
      type=messages.AttachedDisk.TypeValueValuesEnum.SCRATCH,
      autoDelete=True,
      deviceName=device_name,
      interface=maybe_interface_enum,
      mode=messages.AttachedDisk.ModeValueValuesEnum.READ_WRITE,
      initializeParams=messages.AttachedDiskInitializeParams(
          diskType=disk_type),
      )

  if size_bytes is not None:
    local_ssd.diskSizeGb = utils.BytesToGb(size_bytes)

  return local_ssd
