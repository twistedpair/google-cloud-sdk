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
"""Convenience functions for dealing with instance templates."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.compute import alias_ip_range_utils
from googlecloudsdk.api_lib.compute import constants
from googlecloudsdk.api_lib.compute import image_utils
from googlecloudsdk.api_lib.compute import instance_utils
from googlecloudsdk.api_lib.compute import kms_utils
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.api_lib.compute.instances.create import utils as create_utils
from googlecloudsdk.command_lib.compute import scope as compute_scope
from googlecloudsdk.command_lib.compute.networks.subnets import flags as subnet_flags
from googlecloudsdk.core import properties

EPHEMERAL_ADDRESS = object()


def CreateNetworkInterfaceMessage(resources,
                                  scope_lister,
                                  messages,
                                  network,
                                  private_ip,
                                  subnet_region,
                                  subnet,
                                  address,
                                  alias_ip_ranges_string=None,
                                  network_tier=None,
                                  stack_type=None,
                                  ipv6_network_tier=None,
                                  nic_type=None,
                                  ipv6_public_ptr_domain=None):
  """Creates and returns a new NetworkInterface message.

  Args:
    resources: generates resource references,
    scope_lister: function, provides scopes for prompting subnet region,
    messages: GCE API messages,
    network: network,
    private_ip: IPv4 internal IP address to assign to the instance.
    subnet_region: region for subnetwork,
    subnet: regional subnetwork,
    address: specify static address for instance template
               * None - no address,
               * EPHEMERAL_ADDRESS - ephemeral address,
               * string - address name to be fetched from GCE API.
    alias_ip_ranges_string: command line string specifying a list of alias
        IP ranges.
    network_tier: specify network tier for instance template
               * None - no network tier
               * PREMIUM - network tier being PREMIUM
               * SELECT - network tier being SELECT
               * STANDARD - network tier being STANDARD
    stack_type: identify whether IPv6 features are enabled
               * IPV4_ONLY - can only have IPv4 address
               * IPV4_IPV6 - can have both IPv4 and IPv6 address
    ipv6_network_tier: specify network tier for IPv6 access config
               * PREMIUM - network tier being PREMIUM
               * STANDARD - network tier being STANDARD
    nic_type: specify the type of NetworkInterface Controller
               * GVNIC
               * VIRTIO_NET
    ipv6_public_ptr_domain: a string represents the custom PTR domain assigned
        to the interface.
  Returns:
    network_interface: a NetworkInterface message object
  """
  # By default interface is attached to default network. If network or subnet
  # are specified they're used instead.
  network_interface = messages.NetworkInterface()
  if subnet is not None:
    subnet_ref = subnet_flags.SubnetworkResolver().ResolveResources(
        [subnet], compute_scope.ScopeEnum.REGION, subnet_region, resources,
        scope_lister=scope_lister)[0]
    network_interface.subnetwork = subnet_ref.SelfLink()
  if network is not None:
    network_ref = resources.Parse(
        network,
        params={'project': properties.VALUES.core.project.GetOrFail},
        collection='compute.networks')
    network_interface.network = network_ref.SelfLink()
  elif subnet is None:
    network_ref = resources.Parse(
        constants.DEFAULT_NETWORK,
        params={'project': properties.VALUES.core.project.GetOrFail},
        collection='compute.networks')
    network_interface.network = network_ref.SelfLink()

  if private_ip is not None:
    network_interface.networkIP = private_ip

  if stack_type is not None:
    network_interface.stackType = (
        messages.NetworkInterface.StackTypeValueValuesEnum(stack_type))

  if address:
    access_config = messages.AccessConfig(
        name=constants.DEFAULT_ACCESS_CONFIG_NAME,
        type=messages.AccessConfig.TypeValueValuesEnum.ONE_TO_ONE_NAT)

    # If the user provided an external IP, populate the access
    # config with it.
    if address != EPHEMERAL_ADDRESS:
      access_config.natIP = address

    if network_tier is not None:
      access_config.networkTier = (messages.AccessConfig.
                                   NetworkTierValueValuesEnum(network_tier))

    network_interface.accessConfigs = [access_config]

  if ipv6_network_tier is not None or ipv6_public_ptr_domain is not None:
    ipv6_access_config = messages.AccessConfig(
        name=constants.DEFAULT_IPV6_ACCESS_CONFIG_NAME,
        type=messages.AccessConfig.TypeValueValuesEnum.DIRECT_IPV6)
    network_interface.ipv6AccessConfigs = [ipv6_access_config]

  if ipv6_network_tier is not None:
    ipv6_access_config.networkTier = (
        messages.AccessConfig.NetworkTierValueValuesEnum(ipv6_network_tier))

  if ipv6_public_ptr_domain is not None:
    ipv6_access_config.publicPtrDomainName = ipv6_public_ptr_domain

  if alias_ip_ranges_string:
    network_interface.aliasIpRanges = (
        alias_ip_range_utils.CreateAliasIpRangeMessagesFromString(
            messages, False, alias_ip_ranges_string))

  if nic_type is not None:
    network_interface.nicType = (
        messages.NetworkInterface.NicTypeValueValuesEnum(nic_type))

  return network_interface


def CreateNetworkInterfaceMessages(resources, scope_lister, messages,
                                   network_interface_arg, subnet_region):
  """Create network interface messages.

  Args:
    resources: generates resource references,
    scope_lister: function, provides scopes for prompting subnet region,
    messages: creates resources.
    network_interface_arg: CLI argument specifying network interfaces.
    subnet_region: region of the subnetwork.

  Returns:
    list, items are NetworkInterfaceMessages.
  """
  result = []
  if network_interface_arg:
    for interface in network_interface_arg:
      address = interface.get('address', None)
      has_no_address = 'no-address' in interface
      # pylint: disable=g-explicit-bool-comparison
      if address == '' or (address is None and (not has_no_address)):
        address = EPHEMERAL_ADDRESS

      network_tier = interface.get('network-tier', None)
      nic_type = interface.get('nic-type', None)

      result.append(
          CreateNetworkInterfaceMessage(
              resources,
              scope_lister,
              messages,
              interface.get('network', None),
              interface.get('private-network-ip', None),
              subnet_region,
              interface.get('subnet', None),
              address,
              interface.get('aliases', None),
              network_tier,
              nic_type=nic_type,
              stack_type=interface.get('stack-type', None),
              ipv6_network_tier=interface.get('ipv6-network-tier', None),
              ipv6_public_ptr_domain=interface.get('ipv6-public-ptr-domain',
                                                   None)))
  return result


def CreateDiskMessages(args,
                       client,
                       resources,
                       project,
                       image_uri,
                       boot_disk_size_gb=None,
                       create_boot_disk=False,
                       support_kms=False,
                       support_multi_writer=False,
                       support_provisioned_throughput=False,
                       match_container_mount_disks=False
                       ):
  """Create disk messages for a single instance template."""
  container_mount_disk = (
      args.container_mount_disk if match_container_mount_disks else [])

  persistent_disks = (
      CreatePersistentAttachedDiskMessages(
          client.messages, args.disk or [],
          container_mount_disk=container_mount_disk))

  persistent_create_disks = (
      CreatePersistentCreateDiskMessages(
          client,
          resources,
          project,
          getattr(args, 'create_disk', []),
          support_kms=support_kms,
          support_multi_writer=support_multi_writer,
          support_provisioned_throughput=support_provisioned_throughput))

  if create_boot_disk:
    boot_disk_list = [
        CreateDefaultBootAttachedDiskMessage(
            messages=client.messages,
            disk_type=args.boot_disk_type,
            disk_device_name=args.boot_disk_device_name,
            disk_auto_delete=args.boot_disk_auto_delete,
            disk_size_gb=boot_disk_size_gb,
            image_uri=image_uri,
            kms_args=args,
            support_kms=support_kms,
            disk_provisioned_iops=args.boot_disk_provisioned_iops)
    ]
  elif persistent_create_disks and persistent_create_disks[0].boot:
    boot_disk_list = [persistent_create_disks.pop(0)]
  elif persistent_disks and persistent_disks[0].boot:
    boot_disk_list = [persistent_disks.pop(0)]
  else:
    boot_disk_list = []

  local_nvdimms = create_utils.CreateLocalNvdimmMessages(
      args,
      resources,
      client.messages,
  )

  local_ssds = create_utils.CreateLocalSsdMessages(
      args,
      resources,
      client.messages,
  )

  return boot_disk_list + persistent_disks + persistent_create_disks + local_nvdimms + local_ssds


def CreatePersistentAttachedDiskMessages(
    messages, disks, container_mount_disk=None):
  """Returns a list of AttachedDisk messages and the boot disk's reference.

  Args:
    messages: GCE API messages,
    disks: disk objects - contains following properties
             * name - the name of disk,
             * mode - 'rw' (R/W), 'ro' (R/O) access mode,
             * boot - whether it is a boot disk,
             * auto-delete - whether disks is deleted when VM is deleted,
             * device-name - device name on VM.
    container_mount_disk: list of disks to be mounted to container, if any.

  Returns:
    list of API messages for attached disks
  """

  disks_messages = []
  for disk in disks:
    name = disk['name']
    # Resolves the mode.
    mode_value = disk.get('mode', 'rw')
    if mode_value == 'rw':
      mode = messages.AttachedDisk.ModeValueValuesEnum.READ_WRITE
    else:
      mode = messages.AttachedDisk.ModeValueValuesEnum.READ_ONLY

    boot = disk.get('boot', False)
    auto_delete = disk.get('auto-delete', False)
    device_name = instance_utils.GetDiskDeviceName(disk, name,
                                                   container_mount_disk)

    attached_disk = messages.AttachedDisk(
        autoDelete=auto_delete,
        boot=boot,
        deviceName=device_name,
        mode=mode,
        source=name,
        type=messages.AttachedDisk.TypeValueValuesEnum.PERSISTENT)

    # The boot disk must end up at index 0.
    if boot:
      disks_messages = [attached_disk] + disks_messages
    else:
      disks_messages.append(attached_disk)

  return disks_messages


def CreatePersistentCreateDiskMessages(client,
                                       resources,
                                       user_project,
                                       create_disks,
                                       support_kms=False,
                                       container_mount_disk=None,
                                       support_multi_writer=False,
                                       support_provisioned_throughput=False):
  """Returns a list of AttachedDisk messages.

  Args:
    client: Compute client adapter
    resources: Compute resources registry
    user_project: name of user project
    create_disks: disk objects - contains following properties
             * name - the name of disk,
             * description - an optional description for the disk,
             * mode - 'rw' (R/W), 'ro' (R/O) access mode,
             * size - the size of the disk,
             * provisioned-iops - Indicates how many IOPS must be provisioned
               for the disk.
             * provisioned-throughput - Indicates how much throughput is
               provisioned for the disks.
             * type - the type of the disk (HDD or SSD),
             * image - the name of the image to initialize from,
             * image-family - the image family name,
             * image-project - the project name that has the image,
             * auto-delete - whether disks is deleted when VM is deleted ('yes'
               if True),
             * device-name - device name on VM,
             * disk-resource-policy - resource policies applied to disk.

    support_kms: if KMS is supported
    container_mount_disk: list of disks to be mounted to container, if any.
    support_multi_writer: if multi writer disks are supported.
    support_provisioned_throughput: if provisioned throughout is supported.

  Returns:
    list of API messages for attached disks
  """

  disks_messages = []
  messages = client.messages
  for disk in create_disks or []:
    name = disk.get('name')
    # Resolves the mode.
    mode_value = disk.get('mode', 'rw')
    if mode_value == 'rw':
      mode = client.messages.AttachedDisk.ModeValueValuesEnum.READ_WRITE
    else:
      mode = client.messages.AttachedDisk.ModeValueValuesEnum.READ_ONLY

    auto_delete = disk.get('auto-delete', False)
    boot = disk.get('boot', False)
    disk_size_gb = utils.BytesToGb(disk.get('size'))
    img = disk.get('image')
    img_family = disk.get('image-family')
    img_project = disk.get('image-project')

    image_uri = None
    if img or img_family:
      image_expander = image_utils.ImageExpander(client, resources)
      image_uri, _ = image_expander.ExpandImageFlag(
          user_project=user_project,
          image=img,
          image_family=img_family,
          image_project=img_project,
          return_image_resource=False)

    disk_key = None
    if support_kms:
      disk_key = kms_utils.MaybeGetKmsKeyFromDict(
          disk, client.messages, disk_key)

    device_name = instance_utils.GetDiskDeviceName(disk, name,
                                                   container_mount_disk)

    init_params = client.messages.AttachedDiskInitializeParams(
        diskName=name,
        description=disk.get('description'),
        sourceImage=image_uri,
        diskSizeGb=disk_size_gb,
        diskType=disk.get('type'),
        provisionedIops=disk.get('provisioned-iops'))

    policies = disk.get('disk-resource-policy')
    if policies:
      init_params.resourcePolicies = policies

    multi_writer = disk.get('multi-writer')
    if support_multi_writer and multi_writer:
      init_params.multiWriter = True

    disk_architecture = disk.get('architecture')
    if disk_architecture:
      init_params.architecture = messages.AttachedDiskInitializeParams.ArchitectureValueValuesEnum(
          disk_architecture)

    if support_provisioned_throughput:
      init_params.provisionedThroughput = disk.get('provisioned-throughput')

    create_disk = client.messages.AttachedDisk(
        autoDelete=auto_delete,
        boot=boot,
        deviceName=device_name,
        initializeParams=init_params,
        mode=mode,
        type=client.messages.AttachedDisk.TypeValueValuesEnum.PERSISTENT,
        diskEncryptionKey=disk_key)

    # The boot disk must end up at index 0.
    if boot:
      disks_messages = [create_disk] + disks_messages
    else:
      disks_messages.append(create_disk)

  return disks_messages


def CreateDefaultBootAttachedDiskMessage(messages,
                                         disk_type,
                                         disk_device_name,
                                         disk_auto_delete,
                                         disk_size_gb,
                                         image_uri,
                                         kms_args=None,
                                         support_kms=False,
                                         disk_provisioned_iops=None):
  """Returns an AttachedDisk message for creating a new boot disk."""
  disk_key = None

  if support_kms:
    disk_key = kms_utils.MaybeGetKmsKey(
        kms_args, messages, disk_key, boot_disk_prefix=True)

  initialize_params = messages.AttachedDiskInitializeParams(
      sourceImage=image_uri, diskSizeGb=disk_size_gb, diskType=disk_type)

  if disk_provisioned_iops is not None:
    initialize_params.provisionedIops = disk_provisioned_iops

  return messages.AttachedDisk(
      autoDelete=disk_auto_delete,
      boot=True,
      deviceName=disk_device_name,
      initializeParams=initialize_params,
      mode=messages.AttachedDisk.ModeValueValuesEnum.READ_WRITE,
      type=messages.AttachedDisk.TypeValueValuesEnum.PERSISTENT,
      diskEncryptionKey=disk_key)


def CreateAcceleratorConfigMessages(messages, accelerator):
  """Returns a list of accelerator config messages for Instance Templates.

  Args:
    messages: tracked GCE API messages.
    accelerator: accelerator object with the following properties:
        * type: the accelerator's type.
        * count: the number of accelerators to attach. Optional, defaults to 1.

  Returns:
    a list of accelerator config messages that specify the type and number of
    accelerators to attach to an instance.
  """
  if accelerator is None:
    return []

  accelerator_type = accelerator['type']
  accelerator_count = int(accelerator.get('count', 1))
  accelerator_config = messages.AcceleratorConfig(
      acceleratorType=accelerator_type, acceleratorCount=accelerator_count)
  return [accelerator_config]
