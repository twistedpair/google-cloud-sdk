# -*- coding: utf-8 -*- #
# Copyright 2024 Google Inc. All Rights Reserved.
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
"""Utilities for Backup and DR restore command apis."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import types
from typing import Any, Dict, List

from googlecloudsdk.api_lib.compute import alias_ip_range_utils
from googlecloudsdk.api_lib.compute import constants as compute_constants
from googlecloudsdk.calliope import exceptions


class ComputeUtil(object):
  """Util class for Restoring Compute Engine Instance."""

  @staticmethod
  def _HasIpV6AccessConfig(network_interface: Dict[str, Any]) -> bool:
    if ("external-ipv6-address" in network_interface) or (
        "ipv6-public-ptr-domain" in network_interface
    ):
      return True
    return False

  @staticmethod
  def ParserNetworkInterface(
      client_messages: types.ModuleType, network_interfaces
  ):
    """Parses the network interface data into client messages.

    Args:
      client_messages:
      network_interfaces: A dictionary containing the network interface data

    Returns:
      List of parsed client messages for Network Interface

    Raises:
      InvalidArgumentException:
    """
    if network_interfaces is None:
      return None
    messages = list()
    for network_interface in network_interfaces:
      message = client_messages.NetworkInterface()
      access_config = client_messages.AccessConfig()
      access_config_ipv6 = client_messages.AccessConfig()
      if "network" in network_interface:
        message.network = network_interface["network"]
      if "subnet" in network_interface:
        message.subnetwork = network_interface["subnet"]
      if "address" in network_interface:
        message.networkIP = network_interface["address"]
      if "internal-ipv6-address" in network_interface:
        message.ipv6Address = network_interface["internal-ipv6-address"]
        if "internal-ipv6-prefix-length" in network_interface:
          message.internalIpv6PrefixLength = network_interface[
              "internal-ipv6-prefix-length"
          ]
        else:
          raise exceptions.InvalidArgumentException(
              "internal-ipv6-prefix-length",
              "Prefix length of the provided IPv6 address is expected but not"
              " found",
          )
      if "external-ipaddress" in network_interface:
        access_config.natIP = network_interface["external-ipaddress"]
      if "external-ipv6-address" in network_interface:
        access_config_ipv6.externalIpv6 = network_interface[
            "external-ipv6-address"
        ]
        if "external-ipv6-prefix-length" in network_interface:
          access_config_ipv6.externalIpv6PrefixLength = network_interface[
              "external-ipv6-prefix-length"
          ]
        else:
          raise exceptions.InvalidArgumentException(
              "external-ipv6-prefix-length",
              "Prefix length of the provided IPv6 address is expected but not"
              " found",
          )
      if "public-ptr-domain" in network_interface:
        access_config.setPublicPtr = True
        access_config.publicPtrDomainName = network_interface[
            "public-ptr-domain"
        ]
      if "ipv6-public-ptr-domain" in network_interface:
        access_config_ipv6.setPublicPtr = True
        access_config_ipv6.publicPtrDomainName = network_interface[
            "ipv6-public-ptr-domain"
        ]
      if "network-tier" in network_interface:
        access_config.networkTier = (
            client_messages.AccessConfig.NetworkTierValueValuesEnum(
                network_interface["network-tier"]
            )
        )
        access_config_ipv6.networkTier = (
            client_messages.AccessConfig.NetworkTierValueValuesEnum(
                network_interface["network-tier"]
            )
        )
      if "aliases" in network_interface:
        message.aliasIpRanges = (
            alias_ip_range_utils.CreateAliasIpRangeMessagesFromString(
                client_messages,
                True,
                network_interface["aliases"],
            )
        )
      if "stack-type" in network_interface:
        message.stackType = (
            client_messages.NetworkInterface.StackTypeValueValuesEnum(
                network_interface["stack-type"]
            )
        )
      if "queue-count" in network_interface:
        message.queueCount = network_interface["queue-count"]
      if "nic-type" in network_interface:
        message.nicType = (
            client_messages.NetworkInterface.NicTypeValueValuesEnum(
                network_interface["nic-type"]
            )
        )
      if "network-attachment" in network_interface:
        message.networkAttachment = network_interface["network-attachment"]
      # Only one of IPv4 Access config and IPv6 Access Config can exist.
      if ComputeUtil._HasIpV6AccessConfig(network_interface):
        message.ipv6AccessConfigs.extend([access_config_ipv6])
      else:
        message.accessConfigs.extend([access_config])
      messages.append(message)
    return messages

  @staticmethod
  def ParserServiceAccount(
      client_messages: types.ModuleType, service_account: str, scopes: List[str]
  ):
    """Parses the service account data into client messages.

    Args:
      client_messages:
      service_account: An email id of the service account
      scopes: A list containing the scopes

    Returns:
      List of parsed client messages for Service Account
    """

    def _ConvertAliasToScopes(scopes):
      converted_scopes = list()
      for scope in scopes:
        scope = compute_constants.SCOPES.get(scope, [scope])
        converted_scopes.extend(scope)
      return converted_scopes

    if service_account is None:
      service_account = "default"
    if scopes is None:
      scopes = compute_constants.DEFAULT_SCOPES
    return [
        client_messages.ServiceAccount(
            email=service_account, scopes=_ConvertAliasToScopes(scopes)
        )
    ]

  @staticmethod
  def ParserDisks(
      client_messages: types.ModuleType, disks: List[Dict[str, Any]]
  ):
    """Parses the disk data into client messages.

    Args:
      client_messages:
      disks: A list of dictionaries containing the disk data

    Returns:
      List of parsed client messages for Disk
    """
    if disks is None:
      return None
    messages = list()
    for disk in disks:
      message = client_messages.AttachedDisk()
      message.initializeParams = client_messages.InitializeParams()
      if "device-name" in disk:
        message.deviceName = disk["device-name"]
      if "name" in disk:
        message.initializeParams.diskName = disk["name"]
      if "replica-zones" in disk:
        message.initializeParams.replicaZones = disk["replica-zones"]
      messages.append(message)
    return messages

  @staticmethod
  def ParseMetadata(
      client_messages: types.ModuleType, metadata: Dict[str, Any]
  ):
    """Parses the metadata data into client messages.

    Args:
      client_messages:
      metadata: A dictionary containing the metadata

    Returns:
      List of parsed client messages for Metadata
    """
    return client_messages.Metadata(
        items=[
            client_messages.Entry(key=key, value=value)
            for key, value in metadata.items()
        ]
    )

  @staticmethod
  def ParseLabels(client_messages: types.ModuleType, labels: Dict[str, Any]):
    """Parses the labels data into client messages.

    Args:
      client_messages:
      labels: A dictionary containing the labels

    Returns:
      List of parsed client messages for Labels
    """
    return client_messages.ComputeInstanceRestoreProperties.LabelsValue(
        additionalProperties=[
            client_messages.ComputeInstanceRestoreProperties.LabelsValue.AdditionalProperty(
                key=key, value=value
            )
            for key, value in labels.items()
        ]
    )

  @staticmethod
  def ParseAdvancedMachineFeatures(
      client_messages: types.ModuleType,
      enable_uefi_networking: bool,
      threads_per_core: int,
      visible_core_count: int,
  ):
    """Parses the advanced machine features data into client messages.

    Args:
      client_messages:
      enable_uefi_networking:
      threads_per_core:
      visible_core_count:

    Returns:
      List of parsed client messages for AdvancedMachineFeatures
    """
    if (
        enable_uefi_networking is None
        and threads_per_core is None
        and visible_core_count is None
    ):
      return None
    message = client_messages.AdvancedMachineFeatures()
    if enable_uefi_networking is not None:
      message.enableUefiNetworking = enable_uefi_networking
    if threads_per_core is not None:
      message.threadsPerCore = threads_per_core
    if visible_core_count is not None:
      message.visibleCoreCount = visible_core_count
    return message

  @staticmethod
  def ParseAccelerator(
      client_messages: types.ModuleType, accelerator: Dict[str, Any]
  ):
    """Parses the accelerator data into client messages.

    Args:
      client_messages:
      accelerator: A dictionaries containing the accelerator data

    Returns:
      List of parsed client messages for Accelerator
    """
    if accelerator is None or "type" not in accelerator:
      return None

    return [
        client_messages.AcceleratorConfig(
            acceleratorType=accelerator["type"],
            acceleratorCount=accelerator.get("count", 1),
        )
    ]
