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
    ]
    super(ComputeRestoreConfig, self).__init__(supported_flags, *args, **kwargs)


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
        # Few scheduling properties are needed to be set for using GPUs
        # TODO: b/342962091 - Remove the following code on
        # implementing scheduling
        restore_request.computeInstanceRestoreProperties.scheduling = self.messages.Scheduling(
            onHostMaintenance=self.messages.Scheduling.OnHostMaintenanceValueValuesEnum(
                "TERMINATE"
            ),
            automaticRestart=True,
        )

    # MinCpuPlatform
    if "MinCpuPlatform" in restore_config:
      restore_request.computeInstanceRestoreProperties.minCpuPlatform = (
          restore_config["MinCpuPlatform"]
      )

    request = self.messages.BackupdrProjectsLocationsBackupVaultsDataSourcesBackupsRestoreRequest(
        name=resource.RelativeName(), restoreBackupRequest=restore_request
    )
    return self.service.Restore(request)
