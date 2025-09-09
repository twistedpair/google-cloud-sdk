# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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

"""Utility functions for clusters command group."""

import collections
import os
import re
from typing import Any, List

from googlecloudsdk.api_lib.util import messages as messages_util
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.cluster_director.clusters import flag_types
from googlecloudsdk.command_lib.util.apis import yaml_data
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs
from googlecloudsdk.core.util import files


def AddClusterNameArgToParser(parser, api_version=None):
  """Adds a cluster name resource argument."""
  cluster_data = yaml_data.ResourceYAMLData.FromPath(
      "cluster_director.clusters.projects_locations_clusters"
  )
  resource_spec = concepts.ResourceSpec.FromYaml(
      cluster_data.GetData(), is_positional=True, api_version=api_version
  )
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name="cluster",
      concept_spec=resource_spec,
      required=True,
      group_help="""
        Name of the cluster resource.
        Formats: cluster | projects/{project}/locations/{locations}/clusters/{cluster}
      """,
  )
  concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)


def GetClusterFlagType(api_version=None) -> dict[str, Any]:
  """Returns the cluster spec for the given API version."""
  if (
      not api_version
      or api_version not in flag_types.API_VERSION_TO_CLUSTER_FLAG_TYPE
  ):
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  return flag_types.API_VERSION_TO_CLUSTER_FLAG_TYPE[api_version]


class ClusterUtil:
  """Represents a cluster utility class."""

  def __init__(self, args, message_module):
    """Initializes the cluster utility class."""
    self.args = args
    self.message_module = message_module
    self.cluster_ref = self.args.CONCEPTS.cluster.Parse()

  def MakeClusterFromConfig(self):
    """Returns a cluster message from the config JSON string."""
    return messages_util.DictToMessageWithErrorCheck(
        self.args.config, self.message_module.Cluster
    )

  def MakeCluster(self):
    """Returns a cluster message from the granular flags."""
    cluster = self.MakeClusterBasic()
    cluster.networks = self.MakeClusterNetworks()
    cluster.storages = self.MakeClusterStorages()
    cluster.compute = self.MakeClusterCompute()
    cluster.orchestrator = self.message_module.Orchestrator(
        slurm=self.MakeClusterSlurmOrchestrator(cluster)
    )
    return cluster

  def MakeClusterBasic(self):
    """Makes a cluster message with basic fields."""
    cluster_ref = self.args.CONCEPTS.cluster.Parse()
    cluster = self.message_module.Cluster(name=cluster_ref.Name())
    if self.args.IsSpecified("description"):
      cluster.description = self.args.description
    if self.args.IsSpecified("labels"):
      cluster.labels = self.MakeLabels(
          self.args.labels, self.message_module.Cluster.LabelsValue
      )
    return cluster

  def MakeClusterNetworks(self):
    """Makes a cluster message with network fields."""
    networks: List[self.message_module.Network] = []
    if self.args.IsSpecified("create_network"):
      networks.append(
          self.message_module.Network(
              initializeParams=self.message_module.NetworkInitializeParams(
                  network=self._GetNetworkName(self.args.create_network),
              )
          )
      )
    if self.args.IsSpecified("network") and self.args.IsSpecified("subnet"):
      networks.append(
          self.message_module.Network(
              networkSource=self.message_module.NetworkSource(
                  network=self._GetNetworkName(self.args.network),
                  subnetwork=self._GetSubNetworkName(self.args.subnet),
              )
          )
      )
    return networks

  def MakeClusterStorages(self):
    """Makes a cluster message with storage fields."""
    storages: List[self.message_module.Storage] = []
    # Gives a range of 10 to 99 for storage IDs, required for deterministic
    # sorting.
    storage_counter = 10
    if self.args.IsSpecified("create_filestores"):
      for filestore in self.args.create_filestores:
        storage_id = self._GetNextStorageId(storage_counter)
        storage_counter += 1
        storages.append(
            self.message_module.Storage(
                id=storage_id,
                initializeParams=self.message_module.StorageInitializeParams(
                    filestore=self.message_module.FilestoreInitializeParams(
                        filestore=self._GetFilestoreName(filestore.get("name")),
                        tier=filestore.get("tier"),
                        fileShares=[
                            self.message_module.FileShareConfig(
                                capacityGb=filestore.get("sizeGb"),
                                fileShare=filestore.get("fileshare"),
                            )
                        ],
                        protocol=filestore.get("protocol"),
                        description=filestore.get("description"),
                    )
                ),
            )
        )
    if self.args.IsSpecified("filestores"):
      for filestore in self.args.filestores:
        storage_id = self._GetNextStorageId(storage_counter)
        storage_counter += 1
        storages.append(
            self.message_module.Storage(
                id=storage_id,
                storageSource=self.message_module.StorageSource(
                    filestore=self._GetFilestoreName(filestore)
                ),
            )
        )
    if self.args.IsSpecified("create_lustres"):
      for lustre in self.args.create_lustres:
        storage_id = self._GetNextStorageId(storage_counter)
        storage_counter += 1
        storages.append(
            self.message_module.Storage(
                id=storage_id,
                initializeParams=self.message_module.StorageInitializeParams(
                    lustre=self.message_module.LustreInitializeParams(
                        lustre=self._GetLustreName(lustre.get("name")),
                        filesystem=lustre.get("filesystem"),
                        capacityGb=lustre.get("sizeGb"),
                        description=lustre.get("description"),
                    )
                ),
            )
        )
    if self.args.IsSpecified("lustres"):
      for lustre in self.args.lustres:
        storage_id = self._GetNextStorageId(storage_counter)
        storage_counter += 1
        storages.append(
            self.message_module.Storage(
                id=storage_id,
                storageSource=self.message_module.StorageSource(
                    lustre=self._GetLustreName(lustre)
                ),
            )
        )
    if self.args.IsSpecified("create_gcs_buckets"):
      for gcs_bucket in self.args.create_gcs_buckets:
        storage_id = self._GetNextStorageId(storage_counter)
        storage_counter += 1
        gcs = self.message_module.GcsInitializeParams(
            bucket=gcs_bucket.get("name")
        )
        if "storageClass" in gcs_bucket:
          gcs.storageClass = gcs_bucket.get("storageClass")
        if not gcs.storageClass and "enableAutoclass" in gcs_bucket:
          gcs.autoclass = self.message_module.GcsAutoclassConfig(
              enabled=gcs_bucket.get("enableAutoclass")
          )
        # If neither storageClass nor autoclass is set, set storageClass to
        # STORAGE_CLASS_STANDARD by default.
        if not gcs.storageClass and not gcs.autoclass:
          gcs.storageClass = (
              self.message_module.GcsInitializeParams.StorageClassValueValuesEnum.STORAGE_CLASS_STANDARD
          )
        if "enableHNS" in gcs_bucket:
          gcs.hierarchicalNamespace = (
              self.message_module.GcsHierarchicalNamespaceConfig(
                  enabled=gcs_bucket.get("enableHNS"),
              )
          )
        storages.append(
            self.message_module.Storage(
                id=storage_id,
                initializeParams=self.message_module.StorageInitializeParams(
                    gcs=gcs
                ),
            )
        )
    if self.args.IsSpecified("gcs_buckets"):
      for gcs_bucket in self.args.gcs_buckets:
        storage_id = self._GetNextStorageId(storage_counter)
        storage_counter += 1
        storages.append(
            self.message_module.Storage(
                id=storage_id,
                storageSource=self.message_module.StorageSource(
                    bucket=gcs_bucket
                ),
            )
        )
    return storages

  def MakeClusterCompute(self):
    """Makes a cluster message with compute fields."""
    compute = self.message_module.Compute()
    compute_reservation: dict[str, self.message_module.ReservationAffinity] = {}
    if self.args.IsSpecified("compute_resource_reservations"):
      for reservation in self.args.compute_resource_reservations:
        reservation_affinity = self.message_module.ReservationAffinity(
            type=reservation.get("type"),
            key=reservation.get("key"),
            values=[
                self._GetReservationName(value)
                for value in reservation.get("values")
            ],
        )
        if not reservation_affinity.key and reservation_affinity.type in [
            self.message_module.ReservationAffinity.TypeValueValuesEnum.RESERVATION_TYPE_SPECIFIC_RESERVATION,
            self.message_module.ReservationAffinity.TypeValueValuesEnum.RESERVATION_TYPE_ANY_RESERVATION,
        ]:
          reservation_affinity.key = "compute.googleapis.com/reservation-name"
        compute_reservation[reservation.get("computeId")] = reservation_affinity

    compute_disks: dict[str, list[self.message_module.Disk]] = (
        collections.defaultdict(list[self.message_module.Disk])
    )
    if self.args.IsSpecified("compute_resource_disks"):
      for disk in self.args.compute_resource_disks:
        compute_disks[disk.get("computeId")].append(
            self.MakeDisk(disk_args=disk)
        )

    if self.args.IsSpecified("compute_resources"):
      for compute_resource in self.args.compute_resources:
        resource_request = self.message_module.ResourceRequest(
            id=compute_resource.get("name"),
            zone=compute_resource.get("zone"),
            machineType=compute_resource.get("machineType"),
            reservationAffinity=compute_reservation.get(
                compute_resource.get("name")
            ),
            disks=compute_disks[compute_resource.get("name")],
            provisioningModel=compute_resource.get("provisioningModel"),
            maxRunDuration=compute_resource.get("maxRunDuration"),
            terminationAction=compute_resource.get("terminationAction"),
        )
        if {
            "guestAcceleratorType",
            "guestAcceleratorCount",
        } <= compute_resource.keys():
          resource_request.guestAccelerators.append(
              self.message_module.GuestAccelerator(
                  acceleratorType=compute_resource.get("guestAcceleratorType"),
                  count=compute_resource.get("guestAcceleratorCount"),
              )
          )
        compute.resourceRequests.append(resource_request)
    return compute

  def MakeClusterSlurmOrchestrator(self, cluster):
    """Makes a cluster message with slurm orchestrator fields."""
    slurm = self.message_module.SlurmOrchestrator()
    storage_configs: List[self.message_module.StorageConfig] = (
        self._GetStorageConfigs(cluster)
    )
    if self.args.IsSpecified("slurm_node_sets"):
      for node_set in self.args.slurm_node_sets:
        slurm.nodeSets.append(
            self.message_module.SlurmNodeSet(
                id=node_set.get("name"),
                resourceRequestId=node_set.get("computeId"),
                staticNodeCount=node_set.get("staticNodeCount", 1),
                maxDynamicNodeCount=node_set.get("maxDynamicNodeCount"),
                storageConfigs=storage_configs,
                canIpForward=node_set.get("enableIPForward"),
                enableOsLogin=node_set.get("enableOSLogin", True),
                enablePublicIps=node_set.get("enablePublicIPs"),
                serviceAccount=self.MakeServiceAccount(node_set),
                startupScript=self._GetBashScript(
                    node_set.get("startupScript")
                ),
                labels=self.MakeLabels(
                    label_args=node_set.get("labels"),
                    label_cls=self.message_module.SlurmNodeSet.LabelsValue,
                ),
            )
        )

    if self.args.IsSpecified("slurm_partitions"):
      for partition in self.args.slurm_partitions:
        slurm.partitions.append(
            self.message_module.SlurmPartition(
                id=partition.get("name"),
                nodeSetIds=partition.get("nodesetIds"),
                exclusive=partition.get("exclusive"),
            )
        )

    if self.args.IsSpecified("slurm_default_partition"):
      slurm.defaultPartition = self.args.slurm_default_partition

    if self.args.IsSpecified("slurm_login_node"):
      login_node = self.args.slurm_login_node
      slurm.loginNodes = self.message_module.SlurmLoginNodes(
          count=login_node.get("count", 1),
          machineType=login_node.get("machineType"),
          zone=login_node.get("zone"),
          storageConfigs=storage_configs,
          enableOsLogin=login_node.get("enableOSLogin", True),
          enablePublicIps=login_node.get("enablePublicIPs", True),
          serviceAccount=self.MakeServiceAccount(login_node),
          startupScript=self._GetBashScript(login_node.get("startupScript")),
          labels=self.MakeLabels(
              label_args=login_node.get("labels"),
              label_cls=self.message_module.SlurmLoginNodes.LabelsValue,
          ),
      )

    if self.args.IsSpecified("slurm_login_node_disks"):
      for disk in self.args.slurm_login_node_disks:
        slurm.loginNodes.disks.append(self.MakeDisk(disk_args=disk))

    if self.args.IsSpecified("slurm_config"):
      config = self.args.slurm_config
      slurm.config = self.message_module.SlurmConfig(
          requeueExitCodes=config.get("requeueExitCodes"),
          requeueHoldExitCodes=config.get("requeueHoldExitCodes"),
          prologFlags=config.get("prologFlags"),
          prologEpilogTimeout=config.get("prologEpilogTimeout"),
      )
      for script in config.get("jobPrologBashScripts"):
        slurm.prologBashScripts.append(self._GetBashScript(script))
      for script in config.get("jobEpilogBashScripts"):
        slurm.epilogBashScripts.append(self._GetBashScript(script))
      for script in config.get("taskPrologBashScripts"):
        slurm.taskPrologBashScripts.append(self._GetBashScript(script))
      for script in config.get("taskEpilogBashScripts"):
        slurm.taskEpilogBashScripts.append(self._GetBashScript(script))
    return slurm

  def MakeLabels(self, label_args, label_cls):
    """Returns the labels message."""
    if not label_args:
      return None
    return label_cls(
        additionalProperties=[
            label_cls.AdditionalProperty(key=key, value=value)
            for key, value in sorted(label_args.items())
        ]
    )

  def MakeServiceAccount(self, service_account_args):
    """Returns the service account message."""
    email = service_account_args.get("serviceAccountEmail")
    scopes = service_account_args.get("serviceAccountScopes")
    if not email and not scopes:
      return None
    service_account = self.message_module.ServiceAccount()
    if email:
      service_account.email = email
    if scopes:
      service_account.scopes = scopes
    return service_account

  def MakeDisk(self, disk_args):
    """Returns the disk message."""
    return self.message_module.Disk(
        type=disk_args.get("type"),
        sizeGb=disk_args.get("sizeGb"),
        boot=disk_args.get("boot"),
        sourceImage=self._GetDiskSourceImageName(disk_args.get("sourceImage")),
    )

  def _GetNetworkName(self, network) -> str:
    """Returns the network name."""
    project = self.cluster_ref.Parent().projectsId
    return f"projects/{project}/global/networks/{network}"

  def _GetSubNetworkName(self, subnetwork) -> str:
    """Returns the subnetwork name."""
    project = self.cluster_ref.Parent().projectsId
    return f"projects/{project}/{subnetwork}"

  def _GetNextStorageId(self, storage_counter: int) -> str:
    """Returns the next storage ID."""
    return f"storage{storage_counter}"

  def _GetFilestoreName(self, filestore) -> str:
    """Returns the filestore name."""
    project = self.cluster_ref.Parent().projectsId
    return f"projects/{project}/{filestore}"

  def _GetLustreName(self, lustre) -> str:
    """Returns the Lustre name."""
    project = self.cluster_ref.Parent().projectsId
    return f"projects/{project}/{lustre}"

  def _GetDiskSourceImageName(self, source_image) -> str | None:
    """Returns the disk source image."""
    if not source_image:
      return source_image
    project = self.cluster_ref.Parent().projectsId
    return f"projects/{project}/global/images/{source_image}"

  def _GetReservationName(self, reservation) -> str:
    """Returns the reservation name."""
    project = self.cluster_ref.Parent().projectsId
    return f"projects/{project}/{reservation}"

  def _GetStorageConfigs(self, cluster):
    """Returns the storage configs."""
    storage_configs: List[self.message_module.StorageConfig] = []
    sorted_storages = sorted(cluster.storages, key=lambda storage: storage.id)
    if sorted_storages:
      first_storage = sorted_storages[0]
      storage_configs.append(
          self.message_module.StorageConfig(
              id=first_storage.id,
              localMount="/home",
          )
      )
    counters = collections.defaultdict(int)
    for storage in sorted_storages[1:]:
      local_mount = None
      if storage.initializeParams:
        if storage.initializeParams.filestore:
          local_mount = f"/shared{counters['filestore']}"
          counters["filestore"] += 1
        elif storage.initializeParams.lustre:
          local_mount = f"/scratch{counters['lustre']}"
          counters["lustre"] += 1
        elif storage.initializeParams.gcs:
          local_mount = f"/data{counters['bucket']}"
          counters["bucket"] += 1
      if storage.storageSource:
        if storage.storageSource.filestore:
          local_mount = f"/shared{counters['filestore']}"
          counters["filestore"] += 1
        elif storage.storageSource.lustre:
          local_mount = f"/scratch{counters['lustre']}"
          counters["lustre"] += 1
        elif storage.storageSource.bucket:
          local_mount = f"/data{counters['bucket']}"
          counters["bucket"] += 1
      if not local_mount:
        raise exceptions.ToolException(
            "Storage configuration is not supported."
        )

      storage_configs.append(
          self.message_module.StorageConfig(
              id=storage.id,
              localMount=local_mount,
          )
      )
    return storage_configs

  def _GetBashScript(self, arg_value: str) -> str | exceptions.BadFileException:
    """Returns the bash script if argument is a valid bash file path."""
    if not arg_value or not self._CheckIfBashFileFormat(arg_value):
      return arg_value
    path = os.path.normpath(os.path.join(files.GetCWD(), arg_value))
    if not os.path.exists(path) or not os.path.isfile(path):
      raise exceptions.BadFileException(
          f"Script file not found at path={path} resolved from {arg_value}"
      )
    return files.ReadFileContents(path)

  def _CheckIfBashFileFormat(self, arg_value: str) -> bool:
    """Checks if the argument is a bash file format."""
    return re.match(r"^\S*\.(sh|bash)$", arg_value)
