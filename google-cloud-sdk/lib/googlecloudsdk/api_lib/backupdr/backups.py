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
"""Cloud Backup and DR Backups client."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.backupdr import util
from googlecloudsdk.api_lib.backupdr.restore_util import ComputeUtil
from googlecloudsdk.api_lib.backupdr.restore_util import DiskUtil
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.backupdr import util as command_util
from googlecloudsdk.core import resources
from googlecloudsdk.generated_clients.apis.backupdr.v1 import backupdr_v1_messages


class ComputeRestoreConfig(util.RestrictedDict):
  """Restore configuration."""

  def __init__(self, *args, **kwargs):
    supported_flags = [
        "Name",
        "TargetZone",
        "TargetProject",
        "NetworkInterfaces",
        "ServiceAccount",
        "Scopes",
        "NoScopes",
        "CreateDisks",
        "Description",
        "Metadata",
        "Labels",
        "Tags",
        "MachineType",
        "Hostname",
        "EnableUefiNetworking",
        "ThreadsPerCore",
        "VisibleCoreCount",
        "Accelerator",
        "MinCpuPlatform",
        "MaintenancePolicy",
        "Preemptible",
        "RestartOnFailure",
        "MinNodeCpus",
        "ProvisioningModel",
        "InstanceTerminationAction",
        "LocalSsdRecoveryTimeout",
        "NodeAffinityFile",
        "ReservationAffinity",
        "Reservation",
        "EnableDisplayDevice",
        "CanIpForward",
        "PrivateIpv6GoogleAccessType",
        "NetworkPerformanceConfigs",
        "ConfidentialCompute",
        "DeletionProtection",
        "ResourceManagerTags",
        "ResourcePolicies",
        "KeyRevocationActionType",
        "InstanceKmsKey",
    ]
    super(ComputeRestoreConfig, self).__init__(supported_flags, *args, **kwargs)


class DiskRestoreConfig(util.RestrictedDict):
  """Restore configuration."""

  def __init__(self, *args, **kwargs):
    supported_flags = [
        "Name",
        "TargetZone",
        "TargetRegion",
        "TargetProject",
        "ReplicaZones",
        "Description",
        "Labels",
        "Licenses",
        "GuestOsFeatures",
        "ConfidentialCompute",
        "Type",
        "AccessMode",
        "ResourcePolicies",
        "ProvisionedIops",
        "KmsKey",
        "Architecture",
        "Size",
        "ProvisionedThroughput",
        "StoragePool",
        "ClearOverridesFieldMask",
    ]
    super(DiskRestoreConfig, self).__init__(supported_flags, *args, **kwargs)


class BackupsClient(util.BackupDrClientBase):
  """Cloud Backup and DR Backups client."""

  def __init__(self):
    super(BackupsClient, self).__init__()
    self.service = (
        self.client.projects_locations_backupVaults_dataSources_backups
    )

  def Delete(
      self, resource: resources.Resource
  ) -> backupdr_v1_messages.Operation:
    """Deletes the given backup.

    Args:
      resource: The backup to be deleted.

    Returns:
      A long running operation
    """
    request_id = command_util.GenerateRequestId()
    request = self.messages.BackupdrProjectsLocationsBackupVaultsDataSourcesBackupsDeleteRequest(
        name=resource.RelativeName(), requestId=request_id
    )

    return self.service.Delete(request)

  def RestoreCompute(self, resource, restore_config: ComputeRestoreConfig):
    """Restores the given backup.

    Args:
      resource: The backup to be restored.
      restore_config: Restore configuration.

    Returns:
      A long running operation
    """
    restore_request = self.messages.RestoreBackupRequest()
    restore_request.computeInstanceRestoreProperties = (
        self.messages.ComputeInstanceRestoreProperties(
            name=restore_config["Name"],
        )
    )

    restore_request.computeInstanceTargetEnvironment = (
        self.messages.ComputeInstanceTargetEnvironment(
            zone=restore_config["TargetZone"],
            project=restore_config["TargetProject"],
        )
    )

    # Network Interface
    if "NetworkInterfaces" in restore_config:
      network_interfaces_message = ComputeUtil.ParserNetworkInterface(
          self.messages, restore_config["NetworkInterfaces"]
      )
      if network_interfaces_message:
        restore_request.computeInstanceRestoreProperties.networkInterfaces.extend(
            network_interfaces_message
        )

    # Service Account & Scopes
    service_accounts_message = ComputeUtil.ParserServiceAccount(
        self.messages,
        restore_config.get("ServiceAccount", None),
        restore_config.get(
            "Scopes", [] if restore_config.get("NoScopes", False) else None
        ),
    )
    if service_accounts_message:
      restore_request.computeInstanceRestoreProperties.serviceAccounts = (
          service_accounts_message
      )

    # Create Disks
    if "CreateDisks" in restore_config:
      disks_message = ComputeUtil.ParserDisks(
          self.messages, restore_config["CreateDisks"]
      )
      if disks_message:
        restore_request.computeInstanceRestoreProperties.disks.extend(
            disks_message
        )

    # Description
    if "Description" in restore_config:
      restore_request.computeInstanceRestoreProperties.description = (
          restore_config["Description"]
      )

    # Metadata
    if "Metadata" in restore_config:
      metadata_message = ComputeUtil.ParseMetadata(
          self.messages, restore_config["Metadata"]
      )
      if metadata_message:
        restore_request.computeInstanceRestoreProperties.metadata = (
            metadata_message
        )

    # Labels
    if "Labels" in restore_config:
      labels_message = ComputeUtil.ParseLabels(
          self.messages, restore_config["Labels"]
      )
      if labels_message:
        restore_request.computeInstanceRestoreProperties.labels = labels_message

    # Tags
    if "Tags" in restore_config:
      tags_message = self.messages.Tags(items=restore_config["Tags"])
      if tags_message:
        restore_request.computeInstanceRestoreProperties.tags = tags_message

    # Machine Type
    if "MachineType" in restore_config:
      restore_request.computeInstanceRestoreProperties.machineType = (
          restore_config["MachineType"]
      )

    # Hostname
    if "Hostname" in restore_config:
      restore_request.computeInstanceRestoreProperties.hostname = (
          restore_config["Hostname"]
      )

    # AdvancedMachineFeatures
    # EnableUefiNetworking, ThreadsPerCore, VisibleCoreCount
    advanced_machine_features_message = (
        ComputeUtil.ParseAdvancedMachineFeatures(
            self.messages,
            restore_config.get("EnableUefiNetworking", None),
            restore_config.get("ThreadsPerCore", None),
            restore_config.get("VisibleCoreCount", None),
        )
    )
    if advanced_machine_features_message:
      restore_request.computeInstanceRestoreProperties.advancedMachineFeatures = (
          advanced_machine_features_message
      )

    # Accelerator
    if "Accelerator" in restore_config:
      accelerators_message = ComputeUtil.ParseAccelerator(
          self.messages, restore_config["Accelerator"]
      )
      if accelerators_message:
        restore_request.computeInstanceRestoreProperties.guestAccelerators = (
            accelerators_message
        )

    # MinCpuPlatform
    if "MinCpuPlatform" in restore_config:
      restore_request.computeInstanceRestoreProperties.minCpuPlatform = (
          restore_config["MinCpuPlatform"]
      )

    # Scheduling Flags
    if any(
        flag in restore_config
        for flag in [
            "MaintenancePolicy",
            "Preemptible",
            "RestartOnFailure",
            "MinNodeCpus",
            "ProvisioningModel",
            "InstanceTerminationAction",
            "LocalSsdRecoveryTimeout",
            "NodeAffinityFile",
        ]
    ):
      restore_request.computeInstanceRestoreProperties.scheduling = (
          self.messages.Scheduling()
      )

    # MaintenancePolicy
    if "MaintenancePolicy" in restore_config:
      restore_request.computeInstanceRestoreProperties.scheduling.onHostMaintenance = self.messages.Scheduling.OnHostMaintenanceValueValuesEnum(
          restore_config["MaintenancePolicy"]
      )

    # Preemptible
    if "Preemptible" in restore_config:
      restore_request.computeInstanceRestoreProperties.scheduling.preemptible = restore_config[
          "Preemptible"
      ]

    # RestartOnFailure
    if "RestartOnFailure" in restore_config:
      restore_request.computeInstanceRestoreProperties.scheduling.automaticRestart = restore_config[
          "RestartOnFailure"
      ]

    # MinNodeCpus
    if "MinNodeCpus" in restore_config:
      restore_request.computeInstanceRestoreProperties.scheduling.minNodeCpus = restore_config[
          "MinNodeCpus"
      ]

    # ProvisioningModel
    if "ProvisioningModel" in restore_config:
      restore_request.computeInstanceRestoreProperties.scheduling.provisioningModel = self.messages.Scheduling.ProvisioningModelValueValuesEnum(
          restore_config["ProvisioningModel"]
      )

    # InstanceTerminationAction
    if "InstanceTerminationAction" in restore_config:
      restore_request.computeInstanceRestoreProperties.scheduling.instanceTerminationAction = self.messages.Scheduling.InstanceTerminationActionValueValuesEnum(
          restore_config["InstanceTerminationAction"]
      )

    # LocalSsdRecoveryTimeout
    if "LocalSsdRecoveryTimeout" in restore_config:
      restore_request.computeInstanceRestoreProperties.scheduling.localSsdRecoveryTimeout = self.messages.SchedulingDuration(
          seconds=restore_config["LocalSsdRecoveryTimeout"]
      )

    # NodeAffinityFile
    if "NodeAffinityFile" in restore_config:
      restore_request.computeInstanceRestoreProperties.scheduling.nodeAffinities = ComputeUtil.GetNodeAffinitiesFromFile(
          self.messages, restore_config["NodeAffinityFile"]
      )

    # ReservationAffinity & Reservation
    if "ReservationAffinity" in restore_config:
      restore_request.computeInstanceRestoreProperties.reservationAffinity = (
          ComputeUtil.ParseReservationAffinity(
              self.messages,
              restore_config["ReservationAffinity"],
              restore_config.get("Reservation", None),
          )
      )

    # EnableDisplayDevice
    if "EnableDisplayDevice" in restore_config:
      restore_request.computeInstanceRestoreProperties.displayDevice = (
          self.messages.DisplayDevice(
              enableDisplay=restore_config["EnableDisplayDevice"]
          )
      )

    # CanIpForward
    if "CanIpForward" in restore_config:
      restore_request.computeInstanceRestoreProperties.canIpForward = (
          restore_config["CanIpForward"]
      )

    # PrivateIpv6GoogleAccess
    if "PrivateIpv6GoogleAccessType" in restore_config:
      restore_request.computeInstanceRestoreProperties.privateIpv6GoogleAccess = self.messages.ComputeInstanceRestoreProperties.PrivateIpv6GoogleAccessValueValuesEnum(
          restore_config["PrivateIpv6GoogleAccessType"]
      )

    # NetworkPerformanceConfigs
    if "NetworkPerformanceConfigs" in restore_config:
      network_performance_configs = self.messages.NetworkPerformanceConfig()
      if (
          "total-egress-bandwidth-tier"
          in restore_config["NetworkPerformanceConfigs"]
      ):
        network_performance_configs.totalEgressBandwidthTier = self.messages.NetworkPerformanceConfig.TotalEgressBandwidthTierValueValuesEnum(
            restore_config["NetworkPerformanceConfigs"][
                "total-egress-bandwidth-tier"
            ]
        )
      restore_request.computeInstanceRestoreProperties.networkPerformanceConfig = (
          network_performance_configs
      )

    # ConfidentialCompute
    if "ConfidentialCompute" in restore_config:
      restore_request.computeInstanceRestoreProperties.confidentialInstanceConfig = self.messages.ConfidentialInstanceConfig(
          enableConfidentialCompute=restore_config["ConfidentialCompute"]
      )

    # DeletionProtection
    if "DeletionProtection" in restore_config:
      restore_request.computeInstanceRestoreProperties.deletionProtection = (
          restore_config["DeletionProtection"]
      )

    # ResourceManagerTags
    if "ResourceManagerTags" in restore_config:
      restore_request.computeInstanceRestoreProperties.params = self.messages.InstanceParams(
          resourceManagerTags=self.messages.InstanceParams.ResourceManagerTagsValue(
              additionalProperties=[
                  self.messages.InstanceParams.ResourceManagerTagsValue.AdditionalProperty(
                      key=key, value=value
                  )
                  for key, value in restore_config[
                      "ResourceManagerTags"
                  ].items()
              ]
          )
      )

    # ResourcePolicies
    if "ResourcePolicies" in restore_config:
      restore_request.computeInstanceRestoreProperties.resourcePolicies = (
          restore_config["ResourcePolicies"]
      )

    # KeyRevocationActionType
    if "KeyRevocationActionType" in restore_config:
      restore_request.computeInstanceRestoreProperties.keyRevocationActionType = self.messages.ComputeInstanceRestoreProperties.KeyRevocationActionTypeValueValuesEnum(
          restore_config["KeyRevocationActionType"]
      )

    # InstanceKmsKey
    if "InstanceKmsKey" in restore_config:
      restore_request.computeInstanceRestoreProperties.instanceEncryptionKey = (
          self.messages.CustomerEncryptionKey(
              kmsKeyName=restore_config["InstanceKmsKey"],
          )
      )

    request = self.messages.BackupdrProjectsLocationsBackupVaultsDataSourcesBackupsRestoreRequest(
        name=resource.RelativeName(), restoreBackupRequest=restore_request
    )
    return self.service.Restore(request)

  def RestoreDisk(self, resource, restore_config: DiskRestoreConfig):
    """Restores the given backup.

    Args:
      resource: The backup to be restored.
      restore_config: Restore configuration.

    Returns:
      A long running operation
    """
    restore_request = self.messages.RestoreBackupRequest()
    restore_request.diskRestoreProperties = self.messages.DiskRestoreProperties(
        name=restore_config["Name"],
    )

    target_zone = restore_config.get("TargetZone", None)
    target_region = restore_config.get("TargetRegion", None)

    if target_zone is None and target_region is None:
      raise exceptions.InvalidArgumentException(
          "target_zone",
          "Target zone or target region is required for disk restore",
      )

    if target_zone is not None and target_region is not None:
      raise exceptions.InvalidArgumentException(
          "target_zone",
          "Both Target zone and target region cannot be specified for disk"
          " restore",
      )
    if target_zone is not None:
      restore_request.diskTargetEnvironment = (
          self.messages.DiskTargetEnvironment(
              zone=restore_config["TargetZone"],
              project=restore_config["TargetProject"],
          )
      )
    elif target_region is not None:
      restore_request.regionDiskTargetEnvironment = (
          self.messages.RegionDiskTargetEnvironment(
              region=restore_config["TargetRegion"],
              project=restore_config["TargetProject"],
              replicaZones=restore_config["ReplicaZones"],
          )
      )

    # Description
    if "Description" in restore_config:
      restore_request.diskRestoreProperties.description = restore_config[
          "Description"
      ]

    # Labels
    if "Labels" in restore_config:
      labels_message = DiskUtil.ParseLabels(
          self.messages, restore_config["Labels"]
      )
      if labels_message:
        restore_request.diskRestoreProperties.labels = labels_message

    # Licenses
    if "Licenses" in restore_config:
      restore_request.diskRestoreProperties.licenses = restore_config[
          "Licenses"
      ]

    # ConfidentialCompute
    if "ConfidentialCompute" in restore_config:
      restore_request.diskRestoreProperties.enableConfidentialCompute = (
          restore_config["ConfidentialCompute"]
      )

    # Type
    if "Type" in restore_config:
      restore_request.diskRestoreProperties.type = restore_config["Type"]

    # Size
    if "Size" in restore_config:
      restore_request.diskRestoreProperties.sizeGb = restore_config["Size"]

    # StoragePool
    if "StoragePool" in restore_config:
      restore_request.diskRestoreProperties.storagePool = restore_config[
          "StoragePool"
      ]

    # Architecture
    if "Architecture" in restore_config:
      restore_request.diskRestoreProperties.architecture = (
          self.messages.DiskRestoreProperties.ArchitectureValueValuesEnum(
              restore_config["Architecture"]
          )
      )

    # AccessMode
    if "AccessMode" in restore_config:
      restore_request.diskRestoreProperties.accessMode = (
          self.messages.DiskRestoreProperties.AccessModeValueValuesEnum(
              restore_config["AccessMode"]
          )
      )

    # ResourcePolicies
    if "ResourcePolicies" in restore_config:
      restore_request.diskRestoreProperties.resourcePolicy = restore_config[
          "ResourcePolicies"
      ]

    # ProvisionedIops
    if "ProvisionedIops" in restore_config:
      restore_request.diskRestoreProperties.provisionedIops = restore_config[
          "ProvisionedIops"
      ]

    # ProvisionedThroughput
    if "ProvisionedThroughput" in restore_config:
      restore_request.diskRestoreProperties.provisionedThroughput = (
          restore_config["ProvisionedThroughput"]
      )

    # KmsKey
    if "KmsKey" in restore_config:
      restore_request.diskRestoreProperties.diskEncryptionKey = (
          self.messages.CustomerEncryptionKey(
              kmsKeyName=restore_config["KmsKey"],
          )
      )

    # ClearOverridesFieldMask
    if "ClearOverridesFieldMask" in restore_config:
      restore_request.clearOverridesFieldMask = restore_config[
          "ClearOverridesFieldMask"
      ]

    # GuestOsFeatures
    if "GuestOsFeatures" in restore_config:
      guest_os_features = []
      for feature in restore_config["GuestOsFeatures"]:
        guest_os_features.append(
            self.messages.GuestOsFeature(
                type=self.messages.GuestOsFeature.TypeValueValuesEnum(feature)
            )
        )
      restore_request.diskRestoreProperties.guestOsFeature = guest_os_features

    request = self.messages.BackupdrProjectsLocationsBackupVaultsDataSourcesBackupsRestoreRequest(
        name=resource.RelativeName(), restoreBackupRequest=restore_request
    )
    return self.service.Restore(request)

  def ParseUpdate(self, enforced_retention, expire_time):
    updated_backup = self.messages.Backup()
    if enforced_retention is not None:
      updated_backup.enforcedRetentionEndTime = enforced_retention
    if expire_time is not None:
      updated_backup.expireTime = expire_time
    return updated_backup

  def Update(self, resource, backup, update_mask):
    request_id = command_util.GenerateRequestId()
    request = self.messages.BackupdrProjectsLocationsBackupVaultsDataSourcesBackupsPatchRequest(
        backup=backup,
        name=resource.RelativeName(),
        updateMask=update_mask,
        requestId=request_id,
    )
    return self.service.Patch(request)

  def FetchForResourceType(
      self,
      resource,
      resource_type,
      filter_expression=None,
      page_size=None,
      order_by=None,
  ):
    request = self.messages.BackupdrProjectsLocationsBackupVaultsDataSourcesBackupsFetchForResourceTypeRequest(
        parent=resource.RelativeName(),
        resourceType=resource_type,
        pageSize=page_size,
        filter=filter_expression,
        orderBy=order_by,
    )
    return self.service.FetchForResourceType(request)
