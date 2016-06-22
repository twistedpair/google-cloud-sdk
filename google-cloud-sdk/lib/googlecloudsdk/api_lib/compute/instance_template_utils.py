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
"""Convenience functions for dealing with instance templates."""
from googlecloudsdk.api_lib.compute import constants

EPHEMERAL_ADDRESS = object()


# TODO(user): Add unit tests for utilities
def CreateNetworkInterfaceMessage(
    scope_prompter, messages, network, region, subnet, address):
  """Creates and returns a new NetworkInterface message.

  Args:
    scope_prompter: Scope prompter object,
    messages: GCE API messages,
    network: network,
    region: region for subnetwork,
    subnet: regional subnetwork,
    address: specify static address for instance template
               * None - no address,
               * EPHEMERAL_ADDRESS - ephemeral address,
               * string - address name to be fetched from GCE API.

  Returns:
    network_interface: a NetworkInterface message object
  """
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

  if address:
    access_config = messages.AccessConfig(
        name=constants.DEFAULT_ACCESS_CONFIG_NAME,
        type=messages.AccessConfig.TypeValueValuesEnum.ONE_TO_ONE_NAT)

    # If the user provided an external IP, populate the access
    # config with it.
    if address != EPHEMERAL_ADDRESS:
      access_config.natIP = address

    network_interface.accessConfigs = [access_config]

  return network_interface


def CreatePersistentAttachedDiskMessages(messages, disks):
  """Returns a list of AttachedDisk messages and the boot disk's reference.

  Args:
    messages: GCE API messages,
    disks: disk objects - contains following properties
             * name - the name of disk,
             * mode - 'rw' (R/W), 'ro' (R/O) access mode,
             * boot - whether it is a boot disk,
             * autodelete - whether disks is deleted when VM is deleted,
             * device-name - device name on VM.

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

    boot = disk.get('boot') == 'yes'
    auto_delete = disk.get('auto-delete') == 'yes'

    attached_disk = messages.AttachedDisk(
        autoDelete=auto_delete,
        boot=boot,
        deviceName=disk.get('device-name'),
        mode=mode,
        source=name,
        type=messages.AttachedDisk.TypeValueValuesEnum.PERSISTENT)

    # The boot disk must end up at index 0.
    if boot:
      disks_messages = [attached_disk] + disks_messages
    else:
      disks_messages.append(attached_disk)

  return disks_messages


def CreateDefaultBootAttachedDiskMessage(
    messages, disk_type, disk_device_name, disk_auto_delete, disk_size_gb,
    image_uri):
  """Returns an AttachedDisk message for creating a new boot disk."""
  return messages.AttachedDisk(
      autoDelete=disk_auto_delete,
      boot=True,
      deviceName=disk_device_name,
      initializeParams=messages.AttachedDiskInitializeParams(
          sourceImage=image_uri,
          diskSizeGb=disk_size_gb,
          diskType=disk_type),
      mode=messages.AttachedDisk.ModeValueValuesEnum.READ_WRITE,
      type=messages.AttachedDisk.TypeValueValuesEnum.PERSISTENT)

