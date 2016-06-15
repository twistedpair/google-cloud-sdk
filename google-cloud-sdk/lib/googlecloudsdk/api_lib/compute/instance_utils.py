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
import re

from googlecloudsdk.api_lib.compute import constants
from googlecloudsdk.api_lib.compute import csek_utils
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.compute.instances import flags
from googlecloudsdk.third_party.py27 import py27_collections as collections


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


def GetNameForCustom(custom_cpu, custom_memory_mib):
  """Creates a custom machine type name from the desired CPU and memory specs.

  Args:
    custom_cpu: the number of cpu desired for the custom machine type
    custom_memory_mib: the amount of ram desired in MiB for the custom machine
      type instance

  Returns:
    The custom machine type name for the 'instance create' call
  """
  return 'custom-{0}-{1}'.format(custom_cpu, custom_memory_mib)


def InterpretMachineType(machine_type, custom_cpu, custom_memory):
  """Interprets the machine type for the instance.

  Args:
    machine_type: name of existing machine type, eg. n1-standard
    custom_cpu: number of CPU cores for custom machine type,
    custom_memory: amout of RAM memory in bytes for custom machine type,

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
  if custom_cpu or custom_memory:
    if custom_cpu or custom_memory:
      if machine_type:
        raise exceptions.InvalidArgumentException(
            '--machine-type', 'Cannot set both [--machine-type] and '
            '[--custom-cpu]/[--custom-memory] for the same instance.')
      if not custom_cpu:
        raise exceptions.RequiredArgumentException(
            '--custom-cpu', 'Both [--custom-cpu] and [--custom-memory] must be '
            'set to create a custom machine type instance.')
      if not custom_memory:
        raise exceptions.RequiredArgumentException(
            '--custom-memory', 'Both [--custom-cpu] and [--custom-memory] must '
            'be set to create a custom machine type instance.')
      custom_type_string = GetNameForCustom(
          custom_cpu,
          # converting from B to MiB.
          int(custom_memory / (2 ** 20)))

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


def CreateServiceAccountMessages(messages, scopes):
  """Returns a list of ServiceAccount messages corresponding to scopes."""
  if scopes is None:
    scopes = constants.DEFAULT_SCOPES

  accounts_to_scopes = collections.defaultdict(list)
  for scope in scopes:
    parts = scope.split('=')
    if len(parts) == 1:
      account = 'default'
      scope_uri = scope
    elif len(parts) == 2:
      account, scope_uri = parts
    else:
      raise exceptions.ToolException(
          '[{0}] is an illegal value for [--scopes]. Values must be of the '
          'form [SCOPE] or [ACCOUNT=SCOPE].'.format(scope))

    # Expands the scope if the user provided an alias like
    # "compute-rw".
    scope_uri = constants.SCOPES.get(scope_uri, scope_uri)

    accounts_to_scopes[account].append(scope_uri)

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
    scope_prompter, compute_client, project,
    machine_type, custom_cpu, custom_memory, instance_refs):
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
      machine_type, custom_cpu, custom_memory)

  for instance_ref in instance_refs:
    # Check to see if the custom machine type ratio is supported
    CheckCustomCpuRamRatio(compute_client,
                           project,
                           instance_ref.zone,
                           machine_type_name)
    machine_type_uris.append(scope_prompter.CreateZonalReference(
        machine_type_name, instance_ref.zone,
        resource_type='machineTypes').SelfLink())

  return machine_type_uris


def CreateNetworkInterfaceMessage(
    scope_prompter, compute_client,
    network, subnet, private_network_ip, no_address, address,
    instance_refs):
  """Returns a new NetworkInterface message."""
  region = utils.ZoneNameToRegionName(instance_refs[0].zone)

  messages = compute_client.messages
  network_interface = None
  if subnet is not None:
    subnet_ref = scope_prompter.CreateRegionalReference(
        subnet, region, resource_type='subnetworks')
    network_interface = messages.NetworkInterface(
        subnetwork=subnet_ref.SelfLink())
  else:
    network_ref = scope_prompter.CreateGlobalReference(
        network, resource_type='networks')
    network_interface = messages.NetworkInterface(
        network=network_ref.SelfLink())

  if private_network_ip is not None:
    network_interface.networkIP = private_network_ip

  if not no_address:
    access_config = messages.AccessConfig(
        name=constants.DEFAULT_ACCESS_CONFIG_NAME,
        type=messages.AccessConfig.TypeValueValuesEnum.ONE_TO_ONE_NAT)

    # If the user provided an external IP, populate the access
    # config with it.
    # TODO(b/25278937): plays poorly when creating multiple instances
    if len(instance_refs) == 1:
      address_resource = flags.ExpandAddressFlag(
          scope_prompter, compute_client, address, region)
      if address_resource:
        access_config.natIP = address_resource

    network_interface.accessConfigs = [access_config]

  return network_interface


def CreatePersistentAttachedDiskMessages(
    scope_prompter, compute_client, csek_keys, disks, instance_ref):
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

    disk_ref = scope_prompter.CreateZonalReference(
        name, instance_ref.zone,
        resource_type='disks')
    if boot:
      boot_disk_ref = disk_ref

    # TODO(user) drop test after CSEK goes GA
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


def CreateDefaultBootAttachedDiskMessage(
    scope_prompter, compute_client, resources,
    disk_type, disk_device_name, disk_auto_delete, disk_size_gb,
    require_csek_key_create, image_uri, instance_ref,
    csek_keys=None):
  """Returns an AttachedDisk message for creating a new boot disk."""
  messages = compute_client.messages
  compute = compute_client.apitools_client

  if disk_type:
    disk_type_ref = scope_prompter.CreateZonalReference(
        disk_type, instance_ref.zone,
        resource_type='diskTypes')
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

    disk_ref = scope_prompter.CreateZonalReference(
        effective_boot_disk_name, instance_ref.zone,
        resource_type='disks')
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


def CreateLocalSsdMessage(command, device_name, interface, zone=None):
  """Create a message representing a local ssd."""

  if zone:
    disk_type_ref = command.CreateZonalReference('local-ssd', zone,
                                                 resource_type='diskTypes')
    disk_type = disk_type_ref.SelfLink()
  else:
    disk_type = 'local-ssd'

  maybe_interface_enum = (
      command.messages.AttachedDisk.InterfaceValueValuesEnum(interface)
      if interface else None)

  return command.messages.AttachedDisk(
      type=command.messages.AttachedDisk.TypeValueValuesEnum.SCRATCH,
      autoDelete=True,
      deviceName=device_name,
      interface=maybe_interface_enum,
      mode=command.messages.AttachedDisk.ModeValueValuesEnum.READ_WRITE,
      initializeParams=command.messages.AttachedDiskInitializeParams(
          diskType=disk_type),
      )
